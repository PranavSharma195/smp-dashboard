from django.contrib.auth.decorators import login_required
from django.shortcuts import render

from apps.catalog.models import Product
from apps.watchlist import compare as cmp
from apps.watchlist.models import WatchlistItem

from .adapters import available_adapters
from .scoring import DEFAULT_WEIGHTS, DISCLAIMER, LABELS, normalise_weights
from django.conf import settings


@login_required
def trending(request):
    products = list(
        Product.objects.filter(is_active=True).select_related("category", "data_source")
        .order_by("-trend_score", "-viability_score")[:12]
    )
    sample_only = all(p.is_sample for p in products) if products else True
    return render(request, "research/trending.html", {
        "products": products,
        "sample_only": sample_only,
        "watch_ids": set(WatchlistItem.objects.filter(user=request.user).values_list("product_id", flat=True)),
        "compare_ids": set(cmp.get_ids(request)),
        "page_title": "Trending Now",
        "active": "trending",
    })


@login_required
def methodology(request):
    weights = normalise_weights(getattr(settings, "SMP_SCORE_WEIGHTS", DEFAULT_WEIGHTS))
    rows = [(LABELS[k], round(v * 100, 1)) for k, v in weights.items()]
    return render(request, "research/methodology.html", {
        "weights": rows, "disclaimer": DISCLAIMER,
        "adapters": available_adapters(),
        "page_title": "Scoring & data methodology", "active": "trending",
    })
