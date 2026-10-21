from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import Product
from .models import WatchlistItem

User = get_user_model()
AJAX = {"HTTP_X_REQUESTED_WITH": "fetch"}


class Base(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_products", stdout=StringIO())
        cls.user = User.objects.create_user("w1", password="pw-12345-abc")
        cls.other = User.objects.create_user("w2", password="pw-12345-abc")
        cls.products = list(Product.objects.all()[:6])

    def setUp(self):
        self.client.force_login(self.user)


class WatchlistTests(Base):
    def test_add_and_remove(self):
        p = self.products[0]
        r = self.client.post(reverse("watchlist:toggle", args=[p.pk]), **AJAX)
        self.assertEqual(r.json(), {"watching": True, "count": 1, "product": p.name})
        self.assertTrue(WatchlistItem.objects.filter(user=self.user, product=p).exists())
        r = self.client.post(reverse("watchlist:toggle", args=[p.pk]), **AJAX)
        self.assertFalse(r.json()["watching"])
        self.assertEqual(WatchlistItem.objects.count(), 0)

    def test_get_not_allowed(self):
        self.assertEqual(self.client.get(reverse("watchlist:toggle", args=[self.products[0].pk])).status_code, 405)

    def test_watchlist_is_per_user_and_unique(self):
        p = self.products[0]
        self.client.post(reverse("watchlist:toggle", args=[p.pk]), **AJAX)
        self.client.force_login(self.other)
        page = self.client.get(reverse("watchlist:list"))
        self.assertEqual(len(page.context["items"]), 0)
        self.client.post(reverse("watchlist:toggle", args=[p.pk]), **AJAX)
        self.assertEqual(WatchlistItem.objects.count(), 2)

    def test_page_lists_items_and_tradeoff(self):
        for p in self.products[:3]:
            self.client.post(reverse("watchlist:toggle", args=[p.pk]), **AJAX)
        page = self.client.get(reverse("watchlist:list"))
        self.assertEqual(len(page.context["items"]), 3)
        self.assertTrue(page.context["tradeoff"]["from_watchlist"])
        self.assertContains(page, "Low investment or higher return?")

    def test_empty_state(self):
        self.assertContains(self.client.get(reverse("watchlist:list")), "Nothing on your watchlist yet")

    def test_unknown_product_404(self):
        self.assertEqual(self.client.post(reverse("watchlist:toggle", args=[999999]), **AJAX).status_code, 404)

    def test_non_ajax_redirects(self):
        r = self.client.post(reverse("watchlist:toggle", args=[self.products[0].pk]))
        self.assertEqual(r.status_code, 302)


class CompareTests(Base):
    def toggle(self, p):
        return self.client.post(reverse("watchlist:compare_toggle", args=[p.pk]), **AJAX)

    def test_add_remove(self):
        p = self.products[0]
        self.assertTrue(self.toggle(p).json()["in_compare"])
        self.assertEqual(self.client.session["compare_ids"], [p.pk])
        self.assertFalse(self.toggle(p).json()["in_compare"])
        self.assertEqual(self.client.session["compare_ids"], [])

    def test_max_four(self):
        for p in self.products[:4]:
            self.assertEqual(self.toggle(p).status_code, 200)
        r = self.toggle(self.products[4])
        self.assertEqual(r.status_code, 409)
        self.assertIn("up to 4", r.json()["error"])
        self.assertEqual(len(self.client.session["compare_ids"]), 4)

    def test_compare_page_content(self):
        for p in self.products[:3]:
            self.toggle(p)
        page = self.client.get(reverse("watchlist:compare"))
        self.assertEqual(len(page.context["products"]), 3)
        for label in ("MOQ (units)", "Total landed investment", "Gross margin", "Trend score", "Viability score",
                      "Landed cost per unit", "Gross profit per order"):
            self.assertContains(page, label)
        for p in self.products[:3]:
            self.assertContains(page, p.name)

    def test_best_value_highlighted_and_correct(self):
        for p in self.products[:3]:
            self.toggle(p)
        page = self.client.get(reverse("watchlist:compare"))
        row = next(r for r in page.context["rows"] if r["label"] == "Total landed investment")
        lowest = min(p.landed_total_npr for p in page.context["products"])
        self.assertEqual([c["best"] for c in row["cells"]].count(True), 1)
        self.assertTrue(all(c["value"] == lowest for c in row["cells"] if c["best"]))

    def test_no_highlight_for_single_product(self):
        self.toggle(self.products[0])
        page = self.client.get(reverse("watchlist:compare"))
        self.assertFalse(any(c["best"] for r in page.context["rows"] for c in r["cells"]))

    def test_clear_and_empty_state(self):
        self.toggle(self.products[0])
        self.client.post(reverse("watchlist:compare_clear"), **AJAX)
        self.assertContains(self.client.get(reverse("watchlist:compare")), "Pick products to compare")
