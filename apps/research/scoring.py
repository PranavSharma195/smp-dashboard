"""Transparent, rule-based product viability scoring (0-100).

This is an INDICATIVE RESEARCH SCORE. It is a way to compare candidate
products using the assumptions stored in the database. It does not predict
sales and does not guarantee profitability.

Each factor is first converted to a 0-100 sub-score, then combined with
configurable weights (they are normalised, so they need not sum to 1):

    demand        trend/demand score as entered (already 0-100)
    margin        gross margin %; 0 at <=0%, 100 at >= MARGIN_FULL_PCT
    investment    total landed investment; 100 at <= INVEST_LOW, 0 at >= INVEST_HIGH
    competition   low=100, medium=60, high=25
    moq           MOQ affordability; 100 at <= MOQ_LOW, 0 at >= MOQ_HIGH
    complexity    import/sourcing complexity: low=100, medium=65, high=30
    confidence    data confidence: high=100, medium=65, low=30

No Django imports: usable and testable on its own.
"""
from __future__ import annotations

from dataclasses import dataclass

DEFAULT_WEIGHTS = {
    "demand": 0.22,
    "margin": 0.22,
    "investment": 0.14,
    "competition": 0.14,
    "moq": 0.08,
    "complexity": 0.10,
    "confidence": 0.10,
}

MARGIN_FULL_PCT = 60.0
INVEST_LOW = 5_000.0
INVEST_HIGH = 100_000.0
MOQ_LOW = 20
MOQ_HIGH = 500

COMPETITION_POINTS = {"low": 100, "medium": 60, "high": 25}
COMPLEXITY_POINTS = {"low": 100, "medium": 65, "high": 30}
CONFIDENCE_POINTS = {"high": 100, "medium": 65, "low": 30}

LABELS = {
    "demand": "Estimated demand",
    "margin": "Gross margin",
    "investment": "Initial investment",
    "competition": "Competition",
    "moq": "MOQ affordability",
    "complexity": "Sourcing complexity",
    "confidence": "Data confidence",
}

DISCLAIMER = (
    "Indicative research score only. It summarises the assumptions entered for "
    "this product and does not guarantee demand, sales or profit."
)


@dataclass
class ScoreComponent:
    key: str
    label: str
    value: float  # 0-100 sub-score
    weight: float  # normalised weight, sums to 1 across components
    contribution: float  # points added to the total (value x weight)
    note: str


@dataclass
class ScoreResult:
    total: int
    components: list
    disclaimer: str = DISCLAIMER

    def as_dict(self):
        return {
            "total": self.total,
            "disclaimer": self.disclaimer,
            "components": [c.__dict__.copy() for c in self.components],
        }


def _clamp(x, lo=0.0, hi=100.0):
    return max(lo, min(hi, x))


def _num(value, default=0.0):
    try:
        return float(value)
    except (TypeError, ValueError):
        return default


def _level(mapping, value, fallback):
    return mapping.get(str(value).lower(), fallback)


def normalise_weights(weights=None):
    """Return weights restricted to known keys, scaled to sum to 1."""
    raw = dict(DEFAULT_WEIGHTS)
    if weights:
        for key, val in weights.items():
            if key in raw:
                raw[key] = max(0.0, _num(val, raw[key]))
    total = sum(raw.values())
    if total <= 0:
        raw = dict(DEFAULT_WEIGHTS)
        total = sum(raw.values())
    return {k: v / total for k, v in raw.items()}


def score_product(
    *,
    trend_score,
    margin_pct,
    landed_total,
    moq,
    competition,
    complexity,
    confidence,
    weights=None,
) -> ScoreResult:
    """Score a product from its stored assumptions. Missing values score 0."""
    w = normalise_weights(weights)

    margin = _num(margin_pct, 0.0)
    invest = _num(landed_total, INVEST_HIGH)
    moq_n = _num(moq, MOQ_HIGH)

    subs = {
        "demand": _clamp(_num(trend_score)),
        "margin": _clamp(margin / MARGIN_FULL_PCT * 100.0),
        "investment": _clamp(
            (INVEST_HIGH - invest) / (INVEST_HIGH - INVEST_LOW) * 100.0
        ),
        "competition": float(_level(COMPETITION_POINTS, competition, 25)),
        "moq": _clamp((MOQ_HIGH - moq_n) / (MOQ_HIGH - MOQ_LOW) * 100.0),
        "complexity": float(_level(COMPLEXITY_POINTS, complexity, 30)),
        "confidence": float(_level(CONFIDENCE_POINTS, confidence, 30)),
    }
    notes = {
        "demand": f"Demand/trend score of {subs['demand']:.0f}/100 as entered.",
        "margin": f"Gross margin of {margin:.1f}% (full marks at {MARGIN_FULL_PCT:.0f}%).",
        "investment": f"Total landed investment of Rs. {invest:,.0f}; lower is easier to start.",
        "competition": f"{str(competition).title()} competition.",
        "moq": f"Minimum order of {moq_n:.0f} units; smaller MOQs are less risky.",
        "complexity": f"{str(complexity).title()} import complexity.",
        "confidence": f"{str(confidence).title()} confidence in the underlying estimates.",
    }

    components = []
    total = 0.0
    for key in DEFAULT_WEIGHTS:
        contribution = subs[key] * w[key]
        total += contribution
        components.append(
            ScoreComponent(
                key=key,
                label=LABELS[key],
                value=round(subs[key], 1),
                weight=round(w[key], 4),
                contribution=round(contribution, 1),
                note=notes[key],
            )
        )
    return ScoreResult(total=int(round(_clamp(total))), components=components)


def score_band(total):
    """Human label for a score."""
    if total >= 75:
        return "Strong candidate"
    if total >= 60:
        return "Promising"
    if total >= 45:
        return "Worth a closer look"
    return "High risk or thin margin"
