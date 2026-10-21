from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import Product


class DashboardTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_products", stdout=StringIO())
        cls.user = get_user_model().objects.create_user("d1", password="pw-12345-abc")

    def setUp(self):
        self.client.force_login(self.user)

    def test_overview_stats(self):
        r = self.client.get(reverse("dashboard:overview"))
        self.assertEqual(r.status_code, 200)
        s = r.context["stats"]
        self.assertEqual(s["total"], Product.objects.count())
        self.assertEqual(s["trending"], Product.objects.filter(trend_score__gte=70).count())
        self.assertEqual(s["in_budget"], Product.objects.count())  # default range is the full 0-100,000
        self.assertEqual(s["best_profit"], float(max(Product.objects.values_list("profit_per_unit_npr", flat=True))))
        self.assertNotContains(r, "Sample data")
        self.assertContains(r, "chart-data")

    def test_budget_summary_api(self):
        d = self.client.get(reverse("dashboard:summary"), {"budget_min": 10000, "budget_max": 25000}).json()
        self.assertEqual(d["in_budget"], Product.objects.filter(landed_total_npr__gte=10000, landed_total_npr__lte=25000).count())
        self.assertLessEqual(len(d["picks"]), 4)

    def test_budget_summary_swaps_and_ignores_garbage(self):
        a = self.client.get(reverse("dashboard:summary"), {"budget_min": 25000, "budget_max": 10000}).json()
        b = self.client.get(reverse("dashboard:summary"), {"budget_min": 10000, "budget_max": 25000}).json()
        self.assertEqual(a["in_budget"], b["in_budget"])
        c = self.client.get(reverse("dashboard:summary"), {"budget_min": "x", "budget_max": "y"}).json()
        self.assertEqual(c["in_budget"], Product.objects.count())

    def test_overview_with_empty_database(self):
        Product.objects.all().delete()
        self.assertEqual(self.client.get(reverse("dashboard:overview")).status_code, 200)

    def test_every_nav_destination_is_linked(self):
        html = self.client.get(reverse("dashboard:overview")).content.decode()
        for label in ("Overview", "Explore Products", "Trending Now", "Budget Finder", "Product Comparison",
                      "My Watchlist", "Import Cost Calculator", "Settings"):
            self.assertIn(label, html)
