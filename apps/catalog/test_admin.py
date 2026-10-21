from io import StringIO

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import TestCase
from django.urls import reverse

from apps.catalog.models import Product


class AdminTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        call_command("seed_products", stdout=StringIO())
        cls.admin = get_user_model().objects.create_superuser("root", "r@example.com", "pw-12345-abc")

    def setUp(self):
        self.client.force_login(self.admin)

    def test_admin_pages(self):
        for name in ("admin:catalog_product_changelist", "admin:catalog_category_changelist",
                     "admin:catalog_datasource_changelist", "admin:watchlist_watchlistitem_changelist"):
            self.assertEqual(self.client.get(reverse(name)).status_code, 200)
        p = Product.objects.first()
        self.assertEqual(self.client.get(reverse("admin:catalog_product_change", args=[p.pk])).status_code, 200)

    def test_admin_search_and_filter(self):
        r = self.client.get(reverse("admin:catalog_product_changelist"), {"q": "yoga", "competition__exact": "medium"})
        self.assertEqual(r.status_code, 200)

    def test_mark_verified_action(self):
        p = Product.objects.first()
        self.client.post(reverse("admin:catalog_product_changelist"),
                         {"action": "mark_verified", "_selected_action": [p.pk]})
        p.refresh_from_db()
        self.assertTrue(p.is_verified)
        self.assertFalse(p.is_sample)
