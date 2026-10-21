from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import Category, Product
from apps.watchlist.models import WatchlistItem

User = get_user_model()


def make_product(name, cat, **over):
    d = dict(name=name, category=cat, supplier_price_cny=10, moq=100, shipping_npr=5000,
             handling_npr=500, duty_rate_pct=10, other_import_npr=500, selling_price_npr=600,
             trend_score=60, competition="medium", confidence="medium")
    d.update(over)
    return Product.objects.create(**d)


class ProductModelTests(TestCase):
    def test_save_computes_fields(self):
        cat = Category.objects.create(name="Test", slug="test")
        p = make_product("Calc item", cat, supplier_price_cny=10, moq=100, shipping_npr=5000,
                         handling_npr=1000, duty_rate_pct=10, other_import_npr=2000, selling_price_npr=500)
        self.assertEqual(p.slug, "calc-item")
        self.assertEqual(float(p.landed_total_npr), 10 * 18.5 * 100 + 5000 + 1000 + (18500 + 6000) * 0.10 + 2000)
        self.assertEqual(float(p.landed_per_unit_npr), float(p.landed_total_npr) / 100)
        self.assertTrue(0 < p.viability_score <= 100)

    def test_unique_slug(self):
        cat = Category.objects.create(name="Test", slug="test")
        a, b = make_product("Same name", cat), make_product("Same name", cat)
        self.assertNotEqual(a.slug, b.slug)


class SeedTests(TestCase):
    def test_seed_creates_at_least_30_and_is_idempotent(self):
        call_command("seed_products", stdout=StringIO())
        n = Product.objects.count()
        self.assertGreaterEqual(n, 30)
        call_command("seed_products", stdout=StringIO())
        self.assertEqual(Product.objects.count(), n)
        self.assertTrue(Product.objects.filter(is_sample=True, is_verified=False).count() == n)

    def test_seed_covers_every_required_field(self):
        call_command("seed_products", stdout=StringIO())
        for p in Product.objects.all():
            self.assertTrue(p.description and p.why_research and p.estimate_basis)
            self.assertIsNotNone(p.data_source)
            self.assertGreater(p.landed_total_npr, 0)
            self.assertIn(p.confidence, ("low", "medium", "high"))

    def test_seed_has_budget_spread(self):
        call_command("seed_products", stdout=StringIO())
        totals = list(Product.objects.values_list("landed_total_npr", flat=True))
        self.assertLess(min(totals), 20000)
        self.assertGreater(max(totals), 70000)


class AuthedBase(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_products", stdout=StringIO())
        cls.user = User.objects.create_user("tester", password="pw-for-tests-123")

    def setUp(self):
        self.client.force_login(self.user)

    def names(self, **params):
        r = self.client.get(reverse("catalog:api"), params)
        self.assertEqual(r.status_code, 200)
        return r.json()


class ListingAndDetailTests(AuthedBase):
    def test_explore_page_renders(self):
        r = self.client.get(reverse("catalog:explore"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Explore products")
        self.assertContains(r, "Reset filters")

    def test_detail_page(self):
        p = Product.objects.first()
        r = self.client.get(p.get_absolute_url())
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, p.name)
        self.assertContains(r, "Total landed investment")
        self.assertContains(r, "Indicative research score")

    def test_detail_404(self):
        self.assertEqual(self.client.get("/products/does-not-exist/").status_code, 404)

    def test_inactive_hidden(self):
        p = Product.objects.first()
        p.is_active = False
        p.save()
        self.assertEqual(self.client.get(p.get_absolute_url()).status_code, 404)

    def test_other_pages_render(self):
        for name in ("dashboard:overview", "research:trending", "research:methodology",
                     "catalog:budget_finder", "watchlist:list", "watchlist:compare",
                     "finance:calculator", "accounts:settings"):
            with self.subTest(page=name):
                self.assertEqual(self.client.get(reverse(name)).status_code, 200)


class FilterTests(AuthedBase):
    def test_budget_filters_on_total_investment(self):
        data = self.names(budget_min=10000, budget_max=25000)
        self.assertGreater(data["count"], 0)
        for p in Product.objects.filter(landed_total_npr__lt=10000):
            self.assertNotIn(p.name, data["html"])
        qs = Product.objects.filter(landed_total_npr__gte=10000, landed_total_npr__lte=25000)
        self.assertEqual(data["count"], qs.count())

    def test_budget_is_not_unit_price(self):
        # A product with a tiny unit cost but big MOQ must be excluded by a small total budget.
        cat = Category.objects.get(slug="mobile-accessories")
        big = make_product("Cheap unit huge MOQ", cat, supplier_price_cny=1, moq=5000,
                           shipping_npr=30000, selling_price_npr=60)
        self.assertLess(big.landed_per_unit_npr, 100)
        self.assertGreater(big.landed_total_npr, 100000)
        data = self.names(budget_max=20000)
        self.assertNotIn("Cheap unit huge MOQ", data["html"])
        by_unit = self.names(unit_max=100)
        self.assertIn("Cheap unit huge MOQ", by_unit["html"] + self.names(unit_max=100, page=2)["html"])

    def test_reversed_budget_is_swapped(self):
        a = self.names(budget_min=25000, budget_max=10000)["count"]
        b = self.names(budget_min=10000, budget_max=25000)["count"]
        self.assertEqual(a, b)

    def test_moq_filter(self):
        data = self.names(moq_max=50)
        self.assertEqual(data["count"], Product.objects.filter(moq__lte=50).count())
        self.assertGreater(data["count"], 0)
        data = self.names(moq_min=200)
        self.assertEqual(data["count"], Product.objects.filter(moq__gte=200).count())

    def test_unit_cost_filter(self):
        data = self.names(unit_min=100, unit_max=300)
        self.assertEqual(data["count"], Product.objects.filter(landed_per_unit_npr__gte=100, landed_per_unit_npr__lte=300).count())

    def test_category_margin_trend_viability_competition_confidence(self):
        self.assertEqual(self.names(category="fitness")["count"], Product.objects.filter(category__slug="fitness").count())
        self.assertEqual(self.names(margin_min=65)["count"], Product.objects.filter(margin_pct__gte=65).count())
        self.assertEqual(self.names(profit_min=500)["count"], Product.objects.filter(profit_per_unit_npr__gte=500).count())
        self.assertEqual(self.names(trend_min=75)["count"], Product.objects.filter(trend_score__gte=75).count())
        self.assertEqual(self.names(viability_min=80)["count"], Product.objects.filter(viability_score__gte=80).count())
        self.assertEqual(self.names(competition="low")["count"], Product.objects.filter(competition="low").count())
        self.assertEqual(self.names(confidence="medium")["count"], Product.objects.filter(confidence="medium").count())

    def test_search_name_and_description(self):
        self.assertGreaterEqual(self.names(q="yoga")["count"], 1)
        self.assertIn("Yoga", self.names(q="yoga")["html"])
        self.assertGreaterEqual(self.names(q="foldable")["count"], 1)  # description match
        self.assertEqual(self.names(q="zzzznotaproduct")["count"], 0)

    def test_search_multiple_terms_and(self):
        self.assertEqual(self.names(q="yoga mat")["count"], 1)
        self.assertEqual(self.names(q="yoga cable")["count"], 0)

    def test_invalid_params_ignored(self):
        data = self.names(budget_min="abc", moq_max="-5", trend_min="999", sort="evil")
        self.assertEqual(data["count"], Product.objects.count())

    def test_empty_state(self):
        data = self.names(q="zzzznotaproduct")
        self.assertIn("No products match", data["html"])

    def test_pagination(self):
        data = self.names()
        self.assertGreater(data["pages"], 1)
        p2 = self.names(page=2)
        self.assertEqual(p2["page"], 2)
        self.assertNotEqual(data["html"], p2["html"])


class SortTests(AuthedBase):
    def order(self, sort):
        qs = self.client.get(reverse("catalog:explore"), {"sort": sort}).context["products"]
        return list(qs)

    def test_each_sort(self):
        o = self.order("profit")
        self.assertEqual([p.profit_per_order_npr for p in o], sorted((p.profit_per_order_npr for p in o), reverse=True))
        o = self.order("margin")
        self.assertEqual([p.margin_pct for p in o], sorted((p.margin_pct for p in o), reverse=True))
        o = self.order("investment")
        self.assertEqual([p.landed_total_npr for p in o], sorted(p.landed_total_npr for p in o))
        o = self.order("moq")
        self.assertEqual([p.moq for p in o], sorted(p.moq for p in o))
        o = self.order("trend")
        self.assertEqual([p.trend_score for p in o], sorted((p.trend_score for p in o), reverse=True))
        o = self.order("viability")
        self.assertEqual([p.viability_score for p in o], sorted((p.viability_score for p in o), reverse=True))
        o = self.order("recent")
        self.assertEqual([p.created_at for p in o], sorted((p.created_at for p in o), reverse=True))

    def test_lowest_investment_first_item_is_global_minimum(self):
        first = self.order("investment")[0]
        self.assertEqual(first.landed_total_npr, min(Product.objects.values_list("landed_total_npr", flat=True)))


class SavedFiltersTests(AuthedBase):
    def test_save_and_apply(self):
        r = self.client.post(reverse("catalog:save_filters"), {"category": "fitness", "budget_max": "50000"})
        self.assertEqual(r.status_code, 302)
        page = self.client.get(reverse("catalog:explore"))
        self.assertTrue(page.context["used_saved"])
        self.assertEqual(page.context["total"], Product.objects.filter(category__slug="fitness", landed_total_npr__lte=50000).count())
        self.client.post(reverse("catalog:clear_saved_filters"))
        self.assertFalse(self.client.get(reverse("catalog:explore")).context["used_saved"])


class AdapterCommandTests(AuthedBase):
    def test_csv_sync(self):
        import tempfile, os
        p = Product.objects.get(name="Braided USB-C Charging Cable 1m")
        with tempfile.NamedTemporaryFile("w", suffix=".csv", delete=False, encoding="utf-8") as fh:
            fh.write("product_name,field,value,source,verified\n")
            fh.write("Braided USB-C Charging Cable 1m,supplier_price_cny,3.9,Supplier quote test,yes\n")
            fh.write("Braided USB-C Charging Cable 1m,bogus_field,1,Supplier quote test,yes\n")
            path = fh.name
        try:
            call_command("sync_sources", adapter="csv", file=path, stdout=StringIO(), stderr=StringIO())
        finally:
            os.unlink(path)
        p.refresh_from_db()
        self.assertEqual(float(p.supplier_price_cny), 3.9)
        self.assertTrue(p.is_verified)
        self.assertFalse(p.is_sample)
        self.assertEqual(p.data_source.name, "Supplier quote test")
