from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse


class CalculatorViewTests(TestCase):
    def setUp(self):
        self.client.force_login(get_user_model().objects.create_user("c1", password="pw-12345-abc"))

    def test_page_renders_with_assumption_notes(self):
        r = self.client.get(reverse("finance:calculator"))
        self.assertContains(r, "Import cost calculator")
        self.assertContains(r, "Gross profit is not net profit")
        self.assertContains(r, "not live")

    def test_api_matches_formulas(self):
        r = self.client.get(reverse("finance:api"), {
            "unit_price_cny": 10, "fx_rate": 20, "quantity": 100, "shipping_npr": 5000,
            "insurance_handling_npr": 1000, "duty_rate_pct": 10, "other_expenses_npr": 2000, "selling_price_npr": 500})
        d = r.json()
        self.assertTrue(d["valid"])
        self.assertEqual(d["landed_total"], "30600.00")
        self.assertEqual(d["margin_pct"], "38.80")

    def test_api_invalid_input(self):
        d = self.client.get(reverse("finance:api"), {"unit_price_cny": "abc", "fx_rate": 0, "quantity": 0}).json()
        self.assertFalse(d["valid"])
        self.assertGreaterEqual(len(d["errors"]), 3)

    def test_api_empty_query_is_safe(self):
        self.assertFalse(self.client.get(reverse("finance:api")).json()["valid"])

    def test_page_with_bad_query_does_not_crash(self):
        self.assertEqual(self.client.get(reverse("finance:calculator"), {"quantity": "zzz"}).status_code, 200)
