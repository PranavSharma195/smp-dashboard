from django.conf import settings


def site(request):
    from apps.catalog.fx import current_rate

    rate, is_live, fetched_at, fx_source = current_rate()
    ctx = {
        "FX_FETCHED": fetched_at,
        "FX_SOURCE": fx_source,
        "SITE_NAME": settings.SMP_SITE_NAME,
        "SITE_TAGLINE": settings.SMP_SITE_TAGLINE,
        "FX_RATE": rate,
        "FX_IS_LIVE": is_live,
        "COMPARE_MAX": settings.COMPARE_MAX_ITEMS,
        "compare_items": [],
        "watch_count": 0,
    }
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        from apps.catalog.models import Product
        from apps.watchlist import compare as cmp
        from apps.watchlist.models import WatchlistItem

        ids = cmp.get_ids(request)
        if ids:
            found = {p.pk: p for p in Product.objects.filter(pk__in=ids).only("id", "name", "slug")}
            ctx["compare_items"] = [found[i] for i in ids if i in found]
        ctx["watch_count"] = WatchlistItem.objects.filter(user=user).count()
    return ctx
