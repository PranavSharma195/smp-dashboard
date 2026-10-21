"""Session-backed product comparison (max COMPARE_MAX_ITEMS products)."""
from django.conf import settings

SESSION_KEY = "compare_ids"


def get_ids(request):
    ids = request.session.get(SESSION_KEY, [])
    return [i for i in ids if isinstance(i, int)]


def _save(request, ids):
    request.session[SESSION_KEY] = ids
    request.session.modified = True


def toggle(request, product_id):
    """Add or remove a product. Returns (in_compare, error_message_or_None)."""
    ids = get_ids(request)
    limit = getattr(settings, "COMPARE_MAX_ITEMS", 4)
    if product_id in ids:
        ids.remove(product_id)
        _save(request, ids)
        return False, None
    if len(ids) >= limit:
        return False, f"You can compare up to {limit} products. Remove one first."
    ids.append(product_id)
    _save(request, ids)
    return True, None


def clear(request):
    _save(request, [])
