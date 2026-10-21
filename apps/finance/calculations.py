"""Pure-Python import cost and profit calculations.

This module deliberately has NO Django imports so it can be unit-tested and
reused anywhere. All money maths uses ``Decimal`` and is rounded half-up to
two decimal places.

Formulas (all values in NPR unless stated):

    unit_price_npr      = unit_price_cny x fx_rate
    purchase_cost       = unit_price_npr x quantity
    cif_value           = purchase_cost + shipping + insurance_handling
    duties_taxes        = cif_value x duty_rate_pct / 100
    landed_total        = purchase_cost + shipping + insurance_handling
                          + duties_taxes + other_expenses
    landed_per_unit     = landed_total / quantity
    profit_per_unit     = selling_price - landed_per_unit
    profit_per_order    = profit_per_unit x quantity
    margin_pct          = profit_per_unit / selling_price x 100

IMPORTANT: this is GROSS profit. It ignores advertising, platform fees,
storage, returns, local delivery, staff and other operating expenses.
Duty/tax rates are user-supplied ESTIMATES, not verified customs rates.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal, InvalidOperation

TWO_PLACES = Decimal("0.01")
ZERO = Decimal("0")
HUNDRED = Decimal("100")

GROSS_PROFIT_NOTE = (
    "Gross profit is not net profit. Advertising, marketplace fees, storage, "
    "returns, customer delivery, staff and other operating costs will reduce "
    "what you actually earn."
)
DUTY_NOTE = (
    "Customs duty and tax rates are estimates you control. Actual rates depend "
    "on the product's HS classification and current Nepal customs rules; "
    "verify with a customs agent before ordering."
)


def to_decimal(value, default=None):
    """Convert ``value`` to Decimal, returning ``default`` for blank/invalid."""
    if value is None or isinstance(value, bool):
        return default
    if isinstance(value, Decimal):
        result = value
    else:
        text = str(value).strip().replace(",", "")
        if text == "":
            return default
        try:
            result = Decimal(text)
        except (InvalidOperation, ValueError):
            return default
    if not result.is_finite():
        return default
    return result


def money(value):
    """Round to two decimals (half-up). ``None`` passes through."""
    if value is None:
        return None
    return value.quantize(TWO_PLACES, rounding=ROUND_HALF_UP)


@dataclass
class CostBreakdown:
    """Result of an import cost calculation."""

    valid: bool = True
    errors: list = field(default_factory=list)
    quantity: int | None = None
    fx_rate: Decimal | None = None
    unit_price_cny: Decimal | None = None
    unit_price_npr: Decimal | None = None
    purchase_cost: Decimal | None = None
    shipping: Decimal | None = None
    insurance_handling: Decimal | None = None
    duty_rate_pct: Decimal | None = None
    duties_taxes: Decimal | None = None
    other_expenses: Decimal | None = None
    import_expenses_total: Decimal | None = None
    landed_total: Decimal | None = None
    landed_per_unit: Decimal | None = None
    selling_price: Decimal | None = None
    profit_per_unit: Decimal | None = None
    profit_per_order: Decimal | None = None
    margin_pct: Decimal | None = None
    revenue_per_order: Decimal | None = None
    markup_pct: Decimal | None = None
    break_even_price: Decimal | None = None

    def as_dict(self):
        """JSON-friendly dict (Decimals become strings, None stays None)."""
        out = {}
        for key, value in self.__dict__.items():
            out[key] = str(value) if isinstance(value, Decimal) else value
        return out


def compute_import_costs(
    *,
    unit_price_cny,
    fx_rate,
    quantity,
    shipping_npr=0,
    insurance_handling_npr=0,
    duty_rate_pct=0,
    other_expenses_npr=0,
    selling_price_npr=None,
) -> CostBreakdown:
    """Compute landed cost and gross profit for an import order.

    Never raises for bad input: problems are reported through ``errors`` and
    ``valid`` is set to False. Profit fields are ``None`` when no valid selling
    price is available (missing, zero or negative).
    """
    result = CostBreakdown()
    errors = result.errors

    price = to_decimal(unit_price_cny)
    fx = to_decimal(fx_rate)
    qty_dec = to_decimal(quantity)
    ship = to_decimal(shipping_npr, ZERO)
    handling = to_decimal(insurance_handling_npr, ZERO)
    duty_pct = to_decimal(duty_rate_pct, ZERO)
    other = to_decimal(other_expenses_npr, ZERO)
    selling = to_decimal(selling_price_npr)

    if price is None or price < 0:
        errors.append("Supplier price must be zero or more.")
    if fx is None or fx <= 0:
        errors.append("Exchange rate must be greater than zero.")
    qty = None
    if qty_dec is None or qty_dec < 1 or qty_dec != qty_dec.to_integral_value():
        errors.append("Quantity must be a whole number of at least 1.")
    else:
        qty = int(qty_dec)
    for label, value in (
        ("Shipping", ship),
        ("Insurance and handling", handling),
        ("Duty rate", duty_pct),
        ("Other expenses", other),
    ):
        if value < 0:
            errors.append(f"{label} cannot be negative.")
    if duty_pct > 1000:
        errors.append("Duty rate looks unrealistic (over 1000%).")
    if selling is not None and selling < 0:
        errors.append("Selling price cannot be negative.")

    if errors:
        result.valid = False
        return result

    unit_npr = price * fx
    purchase = unit_npr * qty
    cif = purchase + ship + handling
    duties = cif * duty_pct / HUNDRED
    import_total = ship + handling + duties + other
    landed_total = purchase + import_total
    landed_unit = landed_total / qty

    result.quantity = qty
    result.fx_rate = fx
    result.unit_price_cny = price
    result.unit_price_npr = money(unit_npr)
    result.purchase_cost = money(purchase)
    result.shipping = money(ship)
    result.insurance_handling = money(handling)
    result.duty_rate_pct = duty_pct
    result.duties_taxes = money(duties)
    result.other_expenses = money(other)
    result.import_expenses_total = money(import_total)
    result.landed_total = money(landed_total)
    result.landed_per_unit = money(landed_unit)
    result.break_even_price = money(landed_unit)

    if selling is not None and selling > 0:
        profit_unit = selling - landed_unit
        result.selling_price = money(selling)
        result.profit_per_unit = money(profit_unit)
        result.profit_per_order = money(profit_unit * qty)
        result.revenue_per_order = money(selling * qty)
        result.margin_pct = money(profit_unit / selling * HUNDRED)
        if landed_unit > 0:
            result.markup_pct = money(profit_unit / landed_unit * HUNDRED)
    return result
