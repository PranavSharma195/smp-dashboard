from decimal import Decimal

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db.models import Avg, Count
from django.http import Http404, JsonResponse, QueryDict
from django.shortcuts import get_object_or_404, redirect, render
from django.template.loader import render_to_string
from django.views.decorators.http import require_POST

from apps.accounts.models import UserPreference
from apps.finance.calculations import compute_import_costs
from apps.watchlist import compare as cmp
from apps.watchlist.models import WatchlistItem

from .filters import PAGE_SIZE, SORT_OPTIONS, filter_products, parse_filters
from .models import LEVEL_CHOICES, Category, Product


def _flags(request):
    return {
        "watch_ids": set(
            WatchlistItem.objects.filter(user=request.user).values_list("product_id", flat=True)
        ),
        "compare_ids": set(cmp.get_ids(request)),
    }


def _slider_context():
    return {
        "budget_floor": settings.SMP_BUDGET_MIN,
        "budget_ceiling": settings.SMP_BUDGET_MAX,
        "budget_step": settings.SMP_BUDGET_STEP,
    }


def _results(request, params):
    qs, data = filter_products(params)
    paginator = Paginator(qs, PAGE_SIZE)
    page = paginator.get_page(data.get("page"))
    qd = QueryDict(mutable=True)
    for key, value in data.items():
        if key != "page":
            qd[key] = str(value)
    return qs, data, paginator, page, qd.urlencode()


def _grid_html(request, page, empty_hint=True):
    ctx = {"page": page, "products": page.object_list, **_flags(request)}
    return render_to_string("catalog/_grid.html", ctx, request=request)


def _stats(qs):
    agg = qs.aggregate(avg_margin=Avg("margin_pct"), n=Count("id"))
    return {"count": agg["n"], "avg_margin": float(agg["avg_margin"] or 0)}


@login_required
def explore(request):
    params, used_saved = request.GET, False
    pref = UserPreference.objects.filter(user=request.user).first()
    if not params and pref and pref.saved_filters:
        params, used_saved = QueryDict(pref.saved_filters), True
    qs, data, paginator, page, base_qs = _results(request, params)
    ctx = {
        "page": page, "products": page.object_list, "total": paginator.count,
        "filters": data, "base_qs": base_qs, "used_saved": used_saved,
        "categories": Category.objects.all(), "sort_options": SORT_OPTIONS,
        "levels": LEVEL_CHOICES, "sort": data.get("sort", "viability"),
        "page_title": "Explore Products", "active": "explore",
        "has_saved": bool(pref and pref.saved_filters),
        **_slider_context(), **_flags(request),
    }
    return render(request, "catalog/explore.html", ctx)


@login_required
def api_products(request):
    """JSON endpoint used by the live filters (fetch). Returns rendered grid HTML."""
    qs, data, paginator, page, base_qs = _results(request, request.GET)
    stats = _stats(qs)
    return JsonResponse({
        "html": _grid_html(request, page),
        "count": paginator.count,
        "page": page.number,
        "pages": paginator.num_pages,
        "avg_margin": round(stats["avg_margin"], 1),
        "query": base_qs,
    })


@login_required
def budget_finder(request):
    qs, data, paginator, page, base_qs = _results(request, request.GET)
    ctx = {
        "page": page, "products": page.object_list, "total": paginator.count,
        "filters": data, "base_qs": base_qs, "sort_options": SORT_OPTIONS,
        "sort": data.get("sort", "viability"), "categories": Category.objects.all(),
        "page_title": "Budget Finder", "active": "budget",
        "presets": [(0, 10000), (5000, 25000), (25000, 50000), (50000, 100000)],
        **_slider_context(), **_flags(request),
    }
    return render(request, "catalog/budget_finder.html", ctx)


@login_required
def product_detail(request, slug):
    product = get_object_or_404(Product.objects.select_related("category", "data_source"), slug=slug, is_active=True)
    breakdown = product.cost_breakdown()
    score = product.score_breakdown()
    scenarios = []
    for factor in (Decimal("0.8"), Decimal("0.9"), Decimal("1"), Decimal("1.1"), Decimal("1.2")):
        r = compute_import_costs(
            unit_price_cny=product.supplier_price_cny, fx_rate=product.fx_rate, quantity=product.moq,
            shipping_npr=product.shipping_npr, insurance_handling_npr=product.handling_npr,
            duty_rate_pct=product.duty_rate_pct, other_expenses_npr=product.other_import_npr,
            selling_price_npr=product.selling_price_npr * factor,
        )
        scenarios.append({"label": f"{int((factor - 1) * 100):+d}%" if factor != 1 else "Base", "result": r, "base": factor == 1})
    cost_parts = [
        ("Product cost", breakdown.purchase_cost), ("Shipping", breakdown.shipping),
        ("Insurance & handling", breakdown.insurance_handling),
        ("Duties & taxes (est.)", breakdown.duties_taxes), ("Other expenses", breakdown.other_expenses),
    ]
    similar = Product.objects.filter(category=product.category, is_active=True).exclude(pk=product.pk)[:4]
    ctx = {
        "p": product, "b": breakdown, "score": score, "scenarios": scenarios,
        "cost_parts": [(l, float(v or 0)) for l, v in cost_parts], "similar": similar,
        "page_title": product.name, "active": "explore",
        "in_watchlist": WatchlistItem.objects.filter(user=request.user, product=product).exists(),
        "in_compare": product.pk in cmp.get_ids(request), **_flags(request),
    }
    return render(request, "catalog/detail.html", ctx)


@login_required
@require_POST
def save_filters(request):
    data, _form = parse_filters(request.POST)
    data.pop("page", None)
    qd = QueryDict(mutable=True)
    for key, value in data.items():
        qd[key] = str(value)
    pref, _ = UserPreference.objects.get_or_create(user=request.user)
    pref.saved_filters = qd.urlencode()
    pref.save()
    if request.headers.get("X-Requested-With") == "fetch":
        return JsonResponse({"saved": bool(pref.saved_filters), "query": pref.saved_filters})
    return redirect("catalog:explore")


@login_required
@require_POST
def clear_saved_filters(request):
    UserPreference.objects.filter(user=request.user).update(saved_filters="")
    if request.headers.get("X-Requested-With") == "fetch":
        return JsonResponse({"saved": False})
    return redirect("catalog:explore")
