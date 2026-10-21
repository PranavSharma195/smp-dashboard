from decimal import Decimal

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse
from django.shortcuts import render

from apps.catalog.fx import current_rate

from .calculations import DUTY_NOTE, GROSS_PROFIT_NOTE, compute_import_costs

FIELDS = [
    "unit_price_cny", "fx_rate", "quantity", "shipping_npr",
    "insurance_handling_npr", "duty_rate_pct", "other_expenses_npr", "selling_price_npr",
]


def _defaults():
    return {
        "unit_price_cny": "12", "fx_rate": str(current_rate()[0]), "quantity": "100",
        "shipping_npr": "5000", "insurance_handling_npr": "800",
        "duty_rate_pct": settings.SMP_DEFAULT_DUTY_PCT, "other_expenses_npr": "1000",
        "selling_price_npr": "700",
    }


def _calc(params):
    return compute_import_costs(**{f: params.get(f) for f in FIELDS})


@login_required
def calculator(request):
    values = _defaults()
    submitted = any(f in request.GET for f in FIELDS)
    if submitted:
        values.update({f: request.GET.get(f, "") for f in FIELDS})
    result = _calc(values)
    return render(request, "finance/calculator.html", {
        "values": values, "result": result, "submitted": submitted,
        "gross_note": GROSS_PROFIT_NOTE, "duty_note": DUTY_NOTE,
        "fx_is_live": current_rate()[1], "default_fx": current_rate()[0],
        "page_title": "Import Cost Calculator", "active": "calculator",
    })


@login_required
def calculate_api(request):
    result = _calc(request.GET)
    return JsonResponse(result.as_dict())
