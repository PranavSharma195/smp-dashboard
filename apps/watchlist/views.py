from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.db import IntegrityError
from django.http import JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.views.decorators.http import require_POST

from apps.catalog.models import Product

from . import compare as cmp
from .models import WatchlistItem


def _wants_json(request):
    return request.headers.get("X-Requested-With") == "fetch" or "application/json" in request.headers.get("Accept", "")


def _back(request, default="watchlist:list"):
    target = request.POST.get("next") or request.META.get("HTTP_REFERER")
    if target and target.startswith(("/", "http://127.0.0.1", "http://localhost")):
        return redirect(target)
    return redirect(default)


@login_required
def watchlist_page(request):
    items = list(
        WatchlistItem.objects.filter(user=request.user).select_related("product", "product__category")
    )
    products = [i.product for i in items]
    pool = products or list(Product.objects.filter(is_active=True))
    shortlist = sorted(pool, key=lambda p: (-p.viability_score, p.name))[:3]
    tradeoff = None
    if len(pool) >= 2:
        cheapest = min(pool, key=lambda p: p.landed_total_npr)
        top_return = max(pool, key=lambda p: p.profit_per_order_npr)
        tradeoff = {
            "cheapest": cheapest,
            "top_return": top_return,
            "same": cheapest.pk == top_return.pk,
            "from_watchlist": bool(products),
        }
    return render(request, "watchlist/watchlist.html", {
        "items": items,
        "shortlist": shortlist,
        "tradeoff": tradeoff,
        "total_invest": sum((p.landed_total_npr for p in products), 0),
        "page_title": "My Watchlist",
        "active": "watchlist",
        "compare_ids": set(cmp.get_ids(request)),
        "watch_ids": {p.pk for p in products},
    })


@login_required
@require_POST
def watch_toggle(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    item = WatchlistItem.objects.filter(user=request.user, product=product).first()
    if item:
        item.delete()
        watching = False
    else:
        try:
            WatchlistItem.objects.create(user=request.user, product=product)
        except IntegrityError:
            pass
        watching = True
    count = WatchlistItem.objects.filter(user=request.user).count()
    if _wants_json(request):
        return JsonResponse({"watching": watching, "count": count, "product": product.name})
    messages.success(request, f"{'Added' if watching else 'Removed'}: {product.name}")
    return _back(request)


@login_required
@require_POST
def compare_toggle(request, pk):
    product = get_object_or_404(Product, pk=pk, is_active=True)
    in_compare, error = cmp.toggle(request, product.pk)
    ids = cmp.get_ids(request)
    if _wants_json(request):
        names = {p.pk: p for p in Product.objects.filter(pk__in=ids)}
        items = [{"id": i, "name": names[i].name, "slug": names[i].slug} for i in ids if i in names]
        status = 200 if error is None else 409
        return JsonResponse({"in_compare": in_compare, "error": error, "items": items, "count": len(items)}, status=status)
    if error:
        messages.warning(request, error)
    return _back(request, "watchlist:compare")


@login_required
@require_POST
def compare_clear(request):
    cmp.clear(request)
    if _wants_json(request):
        return JsonResponse({"items": [], "count": 0})
    return redirect("watchlist:compare")


COMPARE_ROWS = [
    ("Supplier price (CNY)", "supplier_price_cny", "cny", None),
    ("MOQ (units)", "moq", "int", "min"),
    ("Purchase cost for MOQ", "purchase_cost_npr", "money", "min"),
    ("Import expenses (shipping, duty, other)", "import_expenses_npr", "money", "min"),
    ("Total landed investment", "landed_total_npr", "money", "min"),
    ("Landed cost per unit", "landed_per_unit_npr", "money", "min"),
    ("Est. selling price", "selling_price_npr", "money", None),
    ("Gross profit per unit", "profit_per_unit_npr", "money", "max"),
    ("Gross profit per order", "profit_per_order_npr", "money", "max"),
    ("Gross margin", "margin_pct", "pct", "max"),
    ("Trend score", "trend_score", "int", "max"),
    ("Competition", "competition", "level", None),
    ("Confidence", "confidence", "level", None),
    ("Viability score", "viability_score", "int", "max"),
]


@login_required
def compare_page(request):
    ids = cmp.get_ids(request)
    found = {p.pk: p for p in Product.objects.filter(pk__in=ids, is_active=True).select_related("category")}
    products = [found[i] for i in ids if i in found]
    rows = []
    for label, attr, kind, best in COMPARE_ROWS:
        values = [getattr(p, attr) for p in products]
        best_value = None
        if best and len(products) > 1:
            best_value = min(values) if best == "min" else max(values)
        rows.append({
            "label": label, "kind": kind,
            "cells": [{"value": v, "best": best_value is not None and v == best_value} for v in values],
        })
    return render(request, "watchlist/compare.html", {
        "products": products,
        "rows": rows,
        "page_title": "Product Comparison",
        "active": "compare",
        "watch_ids": set(WatchlistItem.objects.filter(user=request.user).values_list("product_id", flat=True)),
        "max_items": 4,
    })
