from django.test import SimpleTestCase

from .scoring import DEFAULT_WEIGHTS, normalise_weights, score_band, score_product


def args(**over):
    base = dict(trend_score=70, margin_pct=40, landed_total=20000, moq=50,
                competition="medium", complexity="low", confidence="medium")
    base.update(over)
    return base


class ScoringTests(SimpleTestCase):
    def test_range(self):
        for kw in (args(), args(trend_score=0, margin_pct=-50, landed_total=10**7, moq=10**5,
                                competition="high", complexity="high", confidence="low"),
                   args(trend_score=100, margin_pct=500, landed_total=0, moq=1,
                        competition="low", complexity="low", confidence="high")):
            s = score_product(**kw).total
            self.assertTrue(0 <= s <= 100)

    def test_best_and_worst_case(self):
        best = score_product(**args(trend_score=100, margin_pct=60, landed_total=5000, moq=20,
                                    competition="low", complexity="low", confidence="high"))
        worst = score_product(**args(trend_score=0, margin_pct=0, landed_total=100000, moq=500,
                                     competition="high", complexity="high", confidence="low"))
        self.assertEqual(best.total, 100)
        self.assertLess(worst.total, 20)

    def test_components_sum_to_total(self):
        r = score_product(**args())
        self.assertEqual(len(r.components), 7)
        self.assertAlmostEqual(sum(c.contribution for c in r.components), r.total, delta=1.5)
        self.assertAlmostEqual(sum(c.weight for c in r.components), 1.0, places=2)

    def test_higher_margin_scores_higher(self):
        self.assertGreater(score_product(**args(margin_pct=55)).total,
                           score_product(**args(margin_pct=15)).total)

    def test_lower_competition_scores_higher(self):
        self.assertGreater(score_product(**args(competition="low")).total,
                           score_product(**args(competition="high")).total)

    def test_lower_investment_scores_higher(self):
        self.assertGreater(score_product(**args(landed_total=8000)).total,
                           score_product(**args(landed_total=90000)).total)

    def test_custom_weights_change_result(self):
        demand_only = {k: 0 for k in DEFAULT_WEIGHTS}
        demand_only["demand"] = 1
        self.assertEqual(score_product(**args(trend_score=64), weights=demand_only).total, 64)

    def test_weights_are_normalised_and_bad_input_falls_back(self):
        w = normalise_weights({"demand": 10, "margin": 10})
        self.assertAlmostEqual(sum(w.values()), 1.0)
        zero = normalise_weights({k: 0 for k in DEFAULT_WEIGHTS})
        self.assertAlmostEqual(sum(zero.values()), 1.0)

    def test_missing_values_do_not_crash(self):
        r = score_product(trend_score=None, margin_pct=None, landed_total=None, moq=None,
                          competition=None, complexity=None, confidence=None)
        self.assertTrue(0 <= r.total <= 100)

    def test_disclaimer_and_bands(self):
        self.assertIn("does not guarantee", score_product(**args()).disclaimer)
        self.assertEqual(score_band(80), "Strong candidate")
        self.assertEqual(score_band(10), "High risk or thin margin")
