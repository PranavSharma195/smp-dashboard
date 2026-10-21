from decimal import Decimal

from django.test import SimpleTestCase

from .calculations import compute_import_costs, to_decimal
from .formatting import format_compact, format_npr


class CalculationTests(SimpleTestCase):
    def base(self, **over):
        args = dict(unit_price_cny=10, fx_rate=20, quantity=100, shipping_npr=5000,
                    insurance_handling_npr=1000, duty_rate_pct=10, other_expenses_npr=2000,
                    selling_price_npr=500)
        args.update(over)
        return compute_import_costs(**args)

    def test_known_values(self):
        r = self.base()
        # unit = 200; purchase = 20,000; cif = 26,000; duty = 2,600
        self.assertTrue(r.valid)
        self.assertEqual(r.unit_price_npr, Decimal("200.00"))
        self.assertEqual(r.purchase_cost, Decimal("20000.00"))
        self.assertEqual(r.duties_taxes, Decimal("2600.00"))
        self.assertEqual(r.landed_total, Decimal("30600.00"))
        self.assertEqual(r.landed_per_unit, Decimal("306.00"))
        self.assertEqual(r.profit_per_unit, Decimal("194.00"))
        self.assertEqual(r.profit_per_order, Decimal("19400.00"))
        self.assertEqual(r.margin_pct, Decimal("38.80"))

    def test_negative_profit(self):
        r = self.base(selling_price_npr=100)
        self.assertEqual(r.profit_per_unit, Decimal("-206.00"))
        self.assertLess(r.margin_pct, 0)

    def test_zero_selling_price_is_safe(self):
        r = self.base(selling_price_npr=0)
        self.assertTrue(r.valid)
        self.assertIsNone(r.margin_pct)
        self.assertIsNone(r.profit_per_unit)
        self.assertEqual(r.landed_total, Decimal("30600.00"))

    def test_missing_selling_price(self):
        r = self.base(selling_price_npr=None)
        self.assertTrue(r.valid)
        self.assertIsNone(r.profit_per_order)

    def test_optional_costs_default_to_zero(self):
        r = compute_import_costs(unit_price_cny=5, fx_rate=10, quantity=10,
                                 shipping_npr="", insurance_handling_npr=None,
                                 duty_rate_pct="", other_expenses_npr=None, selling_price_npr=100)
        self.assertTrue(r.valid)
        self.assertEqual(r.landed_total, Decimal("500.00"))

    def test_invalid_inputs_report_errors_not_exceptions(self):
        for kwargs in (
            dict(unit_price_cny="abc"), dict(unit_price_cny=-1), dict(fx_rate=0), dict(fx_rate=None),
            dict(quantity=0), dict(quantity="2.5"), dict(quantity="x"), dict(shipping_npr=-5),
            dict(duty_rate_pct=-1), dict(duty_rate_pct=5000), dict(selling_price_npr=-3),
            dict(unit_price_cny="nan"), dict(fx_rate="inf"),
        ):
            with self.subTest(kwargs=kwargs):
                r = self.base(**kwargs)
                self.assertFalse(r.valid)
                self.assertTrue(r.errors)
                self.assertIsNone(r.landed_total)

    def test_comma_numbers_and_strings(self):
        r = self.base(shipping_npr="5,000", quantity="100")
        self.assertEqual(r.landed_total, Decimal("30600.00"))

    def test_rounding_half_up(self):
        r = compute_import_costs(unit_price_cny="1.005", fx_rate=1, quantity=1, selling_price_npr=10)
        self.assertEqual(r.unit_price_npr, Decimal("1.01"))

    def test_to_decimal(self):
        self.assertEqual(to_decimal("1,234.5"), Decimal("1234.5"))
        self.assertIsNone(to_decimal(True))
        self.assertEqual(to_decimal("", 7), 7)

    def test_as_dict_is_json_friendly(self):
        d = self.base().as_dict()
        self.assertEqual(d["landed_total"], "30600.00")
        self.assertTrue(d["valid"])


class FormattingTests(SimpleTestCase):
    def test_nepali_grouping(self):
        self.assertEqual(format_npr(125000), "Rs. 1,25,000")
        self.assertEqual(format_npr(1234567), "Rs. 12,34,567")
        self.assertEqual(format_npr(999), "Rs. 999")
        self.assertEqual(format_npr(0), "Rs. 0")
        self.assertEqual(format_npr(-5000), "-Rs. 5,000")
        self.assertEqual(format_npr(1234.5, 2), "Rs. 1,234.50")

    def test_blank_values(self):
        self.assertEqual(format_npr(None), "—")
        self.assertEqual(format_npr("abc"), "—")

    def test_compact(self):
        self.assertEqual(format_compact(100000), "1L")
        self.assertEqual(format_compact(25000), "25k")
        self.assertEqual(format_compact(500), "500")
