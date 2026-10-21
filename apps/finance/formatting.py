"""Nepali-style currency formatting (pure Python, no Django)."""
from decimal import Decimal, InvalidOperation


def group_nepali(integer_str: str) -> str:
    """Group digits as 1,00,000 (last three, then pairs)."""
    if len(integer_str) <= 3:
        return integer_str
    head, tail = integer_str[:-3], integer_str[-3:]
    parts = []
    while len(head) > 2:
        parts.insert(0, head[-2:])
        head = head[:-2]
    if head:
        parts.insert(0, head)
    return ",".join(parts + [tail])


def format_npr(value, decimals=0, prefix="Rs. "):
    """Format a number like ``Rs. 1,25,000``. Blank/invalid -> an em dash."""
    if value is None or value == "":
        return "—"
    try:
        number = Decimal(str(value))
    except (InvalidOperation, ValueError):
        return "—"
    if not number.is_finite():
        return "—"
    negative = number < 0
    number = abs(number)
    quant = Decimal(1).scaleb(-decimals)
    number = number.quantize(quant)
    text = f"{number:f}"
    integer, _, fraction = text.partition(".")
    out = group_nepali(integer)
    if decimals and fraction:
        out += "." + fraction
    return f"{'-' if negative else ''}{prefix}{out}"


def format_compact(value):
    """Short form for chart axes: 1.2L (lakh), 25k."""
    try:
        n = float(value)
    except (TypeError, ValueError):
        return "—"
    if abs(n) >= 100000:
        return f"{n / 100000:.1f}L".replace(".0L", "L")
    if abs(n) >= 1000:
        return f"{n / 1000:.1f}k".replace(".0k", "k")
    return f"{n:.0f}"
