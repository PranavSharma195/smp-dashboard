from django import template
from django.templatetags.static import static
from django.utils.html import format_html

from apps.finance.formatting import format_compact, format_npr

register = template.Library()


@register.filter
def npr(value, decimals=0):
    """{{ 125000|npr }} -> Rs. 1,25,000"""
    try:
        decimals = int(decimals)
    except (TypeError, ValueError):
        decimals = 0
    return format_npr(value, decimals)


@register.filter
def npr2(value):
    return format_npr(value, 2)


@register.filter
def compact(value):
    return format_compact(value)


@register.filter
def pct(value, decimals=1):
    try:
        return f"{float(value):.{int(decimals)}f}%"
    except (TypeError, ValueError):
        return "—"


@register.filter
def level_class(value):
    return {"low": "lvl-low", "medium": "lvl-med", "high": "lvl-high"}.get(str(value), "")


@register.simple_tag
def icon(name, css="icon"):
    href = f"{static('img/icons.svg')}#{name}"
    return format_html(
        '<svg class="{}" aria-hidden="true" focusable="false"><use href="{}"></use></svg>', css, href
    )


@register.filter
def get_item(mapping, key):
    try:
        return mapping.get(key)
    except AttributeError:
        return None
