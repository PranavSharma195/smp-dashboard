from django.conf import settings
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.contrib.auth.forms import PasswordChangeForm
from django.contrib.auth.views import LoginView
from django.contrib.auth import update_session_auth_hash
from django.shortcuts import redirect, render

from apps.research.scoring import DEFAULT_WEIGHTS, normalise_weights

from apps.catalog.fx import ATTRIBUTION_URL, FxError, current_rate, refresh_rate

from .forms import FriendlyAuthenticationForm
from .models import UserPreference


class SmpLoginView(LoginView):
    template_name = "accounts/login.html"
    authentication_form = FriendlyAuthenticationForm
    redirect_authenticated_user = True


@login_required
def settings_page(request):
    form = PasswordChangeForm(request.user)
    if request.method == "POST":
        form = PasswordChangeForm(request.user, request.POST)
        if form.is_valid():
            user = form.save()
            update_session_auth_hash(request, user)
            messages.success(request, "Password updated.")
            return redirect("accounts:settings")
    weights = normalise_weights(getattr(settings, "SMP_SCORE_WEIGHTS", DEFAULT_WEIGHTS))
    pref = UserPreference.objects.filter(user=request.user).first()
    for f in form.fields.values():
        f.widget.attrs.setdefault("class", "input")
    rate, is_live, fetched_at, fx_source = current_rate()
    return render(request, "accounts/settings.html", {
        "fx_live": is_live, "fx_fetched": fetched_at, "fx_source": fx_source, "fx_attr_url": ATTRIBUTION_URL,
        "form": form,
        "weights": sorted(weights.items(), key=lambda kv: -kv[1]),
        "fx_rate": rate,
        "default_duty": settings.SMP_DEFAULT_DUTY_PCT,
        "saved_filters": pref.saved_filters if pref else "",
        "using_demo_account": request.user.username == settings.SMP_DEMO_USERNAME,
        "page_title": "Settings",
        "active": "settings",
    })


@login_required
def refresh_fx(request):
    if request.method != "POST":
        return redirect("accounts:settings")
    try:
        rate, count = refresh_rate()
    except FxError as exc:
        messages.error(request, str(exc))
    else:
        messages.success(request, f"Live rate fetched: 1 CNY = {rate} NPR. Recalculated {count} products.")
    return redirect("accounts:settings")
