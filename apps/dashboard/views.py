import json
from decimal import Decimal

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.db.models import Avg, Count, Max, Q
from django.http import JsonResponse
from django.shortcuts import render

from apps.catalog.models import Category, Product
from apps.watchlist import compare as cmp
from apps.watchlist.models import WatchlistItem

TRENDING_THRESHOLD = 70


def _num(value):
    return float(value) if value is not None else 0.0


def _budget_params(request):
    try:
        lo = Decimal(request.GET.get("budget_min", settings.SMP_BUDGET_MIN))
        hi = Decimal(request.GET.get("budget_max", settings.SMP_BUDGET_MAX))
    except Exception:
        lo, hi = Decimal(settings.SMP_BUDGET_MIN), Decimal(settings.SMP_BUDGET_MAX)
    lo, hi = max(lo, Decimal(0)), max(hi, Decimal(0))
    if lo > hi:
        lo, hi = hi, lo
    return lo, hi


def _within(qs, lo, hi):
    return qs.filter(landed_total_npr__gte=lo, landed_total_npr__lte=hi)


@login_required
def overview(request):
    active = Product.objects.filter(is_active=True).select_related("category")
    lo, hi = _budget_params(request)
    agg = active.aggregate(
        total=Count("id"),
        trending=Count("id", filter=Q(trend_score__gte=TRENDING_THRESHOLD)),
        best_profit=Max("profit_per_unit_npr"),
        avg_margin=Avg("margin_pct"),
    )
    best = active.order_by("-profit_per_unit_npr").first()
    by_cat = list(
        Category.objects.filter(products__is_active=True)
        .annotate(n=Count("products", filter=Q(products__is_active=True)))
        .order_by("-n", "name")
    )
    top = list(active.order_by("-viability_score", "-margin_pct")[:5])
    recent = list(active.order_by("-created_at", "-id")[:6])
    ranking = list(active.order_by("-trend_score", "-viability_score")[:6])
    chart_products = list(active.order_by("-viability_score")[:8])
    chart = {
        "categories": {"labels": [c.name for c in by_cat], "values": [c.n for c in by_cat]},
        "costs": {
            "labels": [p.name for p in chart_products],
            "cost": [_num(p.landed_per_unit_npr) for p in chart_products],
            "price": [_num(p.selling_price_npr) for p in chart_products],
        },
    }
    in_budget = _within(active, lo, hi)
    ctx = {
        "stats": {
            "total": agg["total"], "trending": agg["trending"],
            "in_budget": in_budget.count(),
            "best_profit": _num(agg["best_profit"]), "best_product": best,
            "avg_margin": _num(agg["avg_margin"]),
        },
        "threshold": TRENDING_THRESHOLD,
        "top": top, "recent": recent, "ranking": ranking,
        "chart_json": json.dumps(chart),
        "by_cat": by_cat,
        "budget_lo": int(lo), "budget_hi": int(hi),
        "budget_floor": settings.SMP_BUDGET_MIN, "budget_ceiling": settings.SMP_BUDGET_MAX,
        "budget_step": settings.SMP_BUDGET_STEP,
        "all_sample": not active.filter(is_sample=False).exists(),
        "watch_ids": set(WatchlistItem.objects.filter(user=request.user).values_list("product_id", flat=True)),
        "compare_ids": set(cmp.get_ids(request)),
        "page_title": "Overview", "active": "overview",
    }
    return render(request, "dashboard/overview.html", ctx)


@login_required
def summary_api(request):
    """Live summary for the dashboard budget slider (no page reload)."""
    lo, hi = _budget_params(request)
    active = Product.objects.filter(is_active=True)
    in_budget = _within(active, lo, hi)
    picks = list(in_budget.order_by("-viability_score")[:4])
    return JsonResponse({
        "in_budget": in_budget.count(),
        "total": active.count(),
        "budget_min": int(lo), "budget_max": int(hi),
        "picks": [
            {"name": p.name, "slug": p.slug, "invest": float(p.landed_total_npr), "score": p.viability_score}
            for p in picks
        ],
    })
