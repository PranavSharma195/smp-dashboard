"""Exchange-rate helper: stored live rate if any, otherwise the illustrative default."""
import json
import urllib.error
import urllib.request
from decimal import Decimal, InvalidOperation

from django.conf import settings

FX_URL = "https://open.er-api.com/v6/latest/CNY"
FX_SOURCE = "open.er-api.com (Exchange Rate API, free tier)"
ATTRIBUTION_URL = "https://www.exchangerate-api.com"


class FxError(Exception):
    """Raised when a live rate cannot be fetched or looks wrong."""


def current_rate():
    """Return (rate, is_live, fetched_at, source)."""
    from .models import FxRate

    latest = FxRate.objects.order_by("-fetched_at").first()
    if latest:
        return latest.rate, True, latest.fetched_at, latest.source
    return Decimal(str(settings.SMP_FX_CNY_TO_NPR)), False, None, "Illustrative default (not live)"


def fetch_live_rate(url=FX_URL, timeout=10):
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:
            payload = json.load(resp)
    except (urllib.error.URLError, TimeoutError, ValueError, OSError) as exc:
        raise FxError(f"Could not reach the exchange-rate service ({exc}). Check your internet connection.") from exc
    if payload.get("result") != "success":
        raise FxError("The exchange-rate service returned an error.")
    try:
        rate = Decimal(str(payload["rates"]["NPR"]))
    except (KeyError, InvalidOperation) as exc:
        raise FxError("The response did not include an NPR rate.") from exc
    if not (Decimal("5") < rate < Decimal("60")):
        raise FxError(f"Rejected implausible CNY to NPR rate: {rate}.")
    return rate


def refresh_rate():
    """Fetch, store, and recalculate every product. Returns (rate, products_updated)."""
    from .models import FxRate, Product

    rate = fetch_live_rate()
    FxRate.objects.create(rate=rate, source=FX_SOURCE)
    count = 0
    for product in Product.objects.all():
        product.save()
        count += 1
    return rate, count
