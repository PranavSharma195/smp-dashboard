from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

User = get_user_model()
PROTECTED = ["dashboard:overview", "catalog:explore", "research:trending", "catalog:budget_finder",
             "watchlist:compare", "watchlist:list", "finance:calculator", "accounts:settings"]


class DemoUserTests(TestCase):
    def test_command_creates_hashed_demo_user(self):
        call_command("ensure_demo_user", stdout=StringIO())
        u = User.objects.get(username="manab")
        self.assertTrue(u.check_password("manab123"))
        self.assertNotEqual(u.password, "manab123")
        self.assertTrue(u.password.startswith("pbkdf2_sha256$"))

    def test_command_is_idempotent_and_keeps_changed_password(self):
        call_command("ensure_demo_user", stdout=StringIO())
        u = User.objects.get(username="manab")
        u.set_password("something-else-456")
        u.save()
        call_command("ensure_demo_user", stdout=StringIO())
        self.assertEqual(User.objects.filter(username="manab").count(), 1)
        self.assertTrue(User.objects.get(username="manab").check_password("something-else-456"))

    def test_reset_password_flag(self):
        call_command("ensure_demo_user", stdout=StringIO())
        u = User.objects.get(username="manab")
        u.set_password("changed-789")
        u.save()
        call_command("ensure_demo_user", "--reset-password", stdout=StringIO())
        self.assertTrue(User.objects.get(username="manab").check_password("manab123"))

    def test_no_plaintext_password_in_settings_source(self):
        from pathlib import Path
        from django.conf import settings
        text = (Path(settings.BASE_DIR) / "config" / "settings.py").read_text()
        self.assertNotIn("manab123", text)


class LoginTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("ensure_demo_user", stdout=StringIO())

    def test_login_page_renders(self):
        self.assertEqual(self.client.get(reverse("accounts:login")).status_code, 200)

    def test_correct_credentials(self):
        r = self.client.post(reverse("accounts:login"), {"username": "manab", "password": "manab123"})
        self.assertRedirects(r, reverse("dashboard:overview"), fetch_redirect_response=False)
        self.assertEqual(self.client.get(reverse("dashboard:overview")).status_code, 200)

    def test_wrong_password(self):
        r = self.client.post(reverse("accounts:login"), {"username": "manab", "password": "nope"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "don&#x27;t match")
        self.assertNotIn("_auth_user_id", self.client.session)

    def test_unknown_user_and_blank(self):
        r = self.client.post(reverse("accounts:login"), {"username": "ghost", "password": "x"})
        self.assertContains(r, "don&#x27;t match")
        r = self.client.post(reverse("accounts:login"), {"username": "", "password": ""})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Please enter")

    def test_authenticated_user_redirected_from_login(self):
        self.client.login(username="manab", password="manab123")
        r = self.client.get(reverse("accounts:login"))
        self.assertRedirects(r, reverse("dashboard:overview"), fetch_redirect_response=False)

    def test_logout(self):
        self.client.login(username="manab", password="manab123")
        r = self.client.post(reverse("accounts:logout"))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(self.client.get(reverse("dashboard:overview")).status_code, 302)

    def test_protected_pages_redirect_when_anonymous(self):
        for name in PROTECTED:
            with self.subTest(page=name):
                r = self.client.get(reverse(name))
                self.assertEqual(r.status_code, 302)
                self.assertIn(reverse("accounts:login"), r["Location"])

    def test_protected_apis_and_actions_require_login(self):
        for url in (reverse("catalog:api"), reverse("finance:api"), reverse("dashboard:summary")):
            self.assertEqual(self.client.get(url).status_code, 302)
        self.assertEqual(self.client.post(reverse("watchlist:toggle", args=[1])).status_code, 302)

    def test_password_change(self):
        self.client.login(username="manab", password="manab123")
        r = self.client.post(reverse("accounts:settings"), {
            "old_password": "manab123", "new_password1": "A-much-better-pass-93", "new_password2": "A-much-better-pass-93"})
        self.assertEqual(r.status_code, 302)
        self.assertTrue(User.objects.get(username="manab").check_password("A-much-better-pass-93"))


class FxTests(TestCase):
    def setUp(self):
        call_command("ensure_demo_user", stdout=StringIO())
        self.client.login(username="manab", password="manab123")

    def _fake(self, payload):
        import io
        import json
        from unittest import mock

        resp = io.BytesIO(json.dumps(payload).encode())
        resp.__enter__ = lambda s: s
        resp.__exit__ = lambda s, *a: False
        return mock.patch("apps.catalog.fx.urllib.request.urlopen", return_value=resp)

    def test_default_rate_is_not_live(self):
        from apps.catalog.fx import current_rate
        rate, live, fetched, _src = current_rate()
        self.assertFalse(live)
        self.assertIsNone(fetched)

    def test_refresh_stores_rate_and_recalculates(self):
        from apps.catalog.models import FxRate, Product
        call_command("seed_products", stdout=StringIO())
        before = Product.objects.first().landed_total_npr
        with self._fake({"result": "success", "rates": {"NPR": 20.0}}):
            r = self.client.post(reverse("accounts:refresh_fx"))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(FxRate.objects.count(), 1)
        self.assertNotEqual(Product.objects.get(pk=Product.objects.first().pk).landed_total_npr, before)

    def test_implausible_or_failed_response_is_rejected(self):
        from apps.catalog.models import FxRate
        with self._fake({"result": "success", "rates": {"NPR": 999}}):
            self.client.post(reverse("accounts:refresh_fx"))
        with self._fake({"result": "error"}):
            self.client.post(reverse("accounts:refresh_fx"))
        self.assertEqual(FxRate.objects.count(), 0)
