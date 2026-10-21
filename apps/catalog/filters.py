"""Validated product filtering and sorting.

Budget semantics (important):
    budget_min / budget_max  -> TOTAL landed investment for the minimum order
                                (purchase + shipping + duties + other).
    unit_min / unit_max      -> landed cost PER UNIT.
A cheap unit price with a huge MOQ can still be unaffordable, so the budget
slider deliberately filters on the total order, not the unit price.
"""
from django import forms
from django.db.models import Q

from .models import LEVEL_CHOICES, Product

SORT_OPTIONS = [
    ("viability", "Highest viability score", ("-viability_score", "-margin_pct", "name")),
    ("profit", "Highest potential profit", ("-profit_per_order_npr", "name")),
    ("margin", "Highest profit margin", ("-margin_pct", "name")),
    ("investment", "Lowest initial investment", ("landed_total_npr", "name")),
    ("moq", "Lowest MOQ", ("moq", "landed_total_npr")),
    ("trend", "Highest trend score", ("-trend_score", "-viability_score")),
    ("recent", "Recently added", ("-created_at", "-id")),
]
SORT_MAP = {key: order for key, _label, order in SORT_OPTIONS}
DEFAULT_SORT = "viability"
PAGE_SIZE = 12


def _dec(label, **kw):
    return forms.DecimalField(required=False, label=label, max_digits=14, decimal_places=2, **kw)


class ProductFilterForm(forms.Form):
    q = forms.CharField(required=False, max_length=100)
    category = forms.SlugField(required=False, max_length=140)
    budget_min = _dec("Min total investment", min_value=0)
    budget_max = _dec("Max total investment", min_value=0)
    unit_min = _dec("Min cost per unit", min_value=0)
    unit_max = _dec("Max cost per unit", min_value=0)
    moq_min = forms.IntegerField(required=False, min_value=0)
    moq_max = forms.IntegerField(required=False, min_value=0)
    margin_min = _dec("Min margin %", min_value=-1000, max_value=1000)
    profit_min = _dec("Min profit per unit", min_value=-10_000_000)
    trend_min = forms.IntegerField(required=False, min_value=0, max_value=100)
    viability_min = forms.IntegerField(required=False, min_value=0, max_value=100)
    competition = forms.ChoiceField(required=False, choices=[("", "Any")] + LEVEL_CHOICES)
    confidence = forms.ChoiceField(required=False, choices=[("", "Any")] + LEVEL_CHOICES)
    sort = forms.ChoiceField(required=False, choices=[(k, l) for k, l, _ in SORT_OPTIONS])
    page = forms.IntegerField(required=False, min_value=1)


def _swap_if_reversed(data, low, high):
    lo, hi = data.get(low), data.get(high)
    if lo is not None and hi is not None and lo > hi:
        data[low], data[high] = hi, lo


def parse_filters(params):
    """Return (cleaned_dict, form). Invalid fields are silently dropped."""
    form = ProductFilterForm(params)
    form.is_valid()
    data = {k: v for k, v in form.cleaned_data.items() if v not in (None, "")}
    _swap_if_reversed(data, "budget_min", "budget_max")
    _swap_if_reversed(data, "unit_min", "unit_max")
    _swap_if_reversed(data, "moq_min", "moq_max")
    return data, form


def filter_products(params, queryset=None):
    """Apply filters and sorting to the active products. Returns (qs, cleaned)."""
    qs = queryset if queryset is not None else Product.objects.filter(is_active=True)
    qs = qs.select_related("category", "data_source")
    data, _form = parse_filters(params)

    for term in data.get("q", "").split():
        qs = qs.filter(
            Q(name__icontains=term)
            | Q(description__icontains=term)
            | Q(category__name__icontains=term)
        )
    if "category" in data:
        qs = qs.filter(category__slug=data["category"])

    ranges = [
        ("budget_min", "landed_total_npr__gte"),
        ("budget_max", "landed_total_npr__lte"),
        ("unit_min", "landed_per_unit_npr__gte"),
        ("unit_max", "landed_per_unit_npr__lte"),
        ("moq_min", "moq__gte"),
        ("moq_max", "moq__lte"),
        ("margin_min", "margin_pct__gte"),
        ("profit_min", "profit_per_unit_npr__gte"),
        ("trend_min", "trend_score__gte"),
        ("viability_min", "viability_score__gte"),
        ("competition", "competition"),
        ("confidence", "confidence"),
    ]
    for key, lookup in ranges:
        if key in data:
            qs = qs.filter(**{lookup: data[key]})

    sort = data.get("sort", DEFAULT_SORT)
    qs = qs.order_by(*SORT_MAP.get(sort, SORT_MAP[DEFAULT_SORT]))
    return qs, data
