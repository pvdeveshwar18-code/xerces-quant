import unittest
from ui.tabs.options_visualizer import calculate_option_greeks, generate_payoff_diagram

class TestOptionsVisualizer(unittest.TestCase):
    def test_calculate_option_greeks(self):
        g_call = calculate_option_greeks(spot=100.0, strike=100.0, dte=30, iv=0.20, option_type="call")
        self.assertIn("delta", g_call)
        self.assertIn("gamma", g_call)
        self.assertIn("theta", g_call)
        self.assertIn("vega", g_call)
        self.assertIn("premium", g_call)
        self.assertAlmostEqual(g_call["delta"], 0.50, delta=0.15)

        g_put = calculate_option_greeks(spot=100.0, strike=100.0, dte=30, iv=0.20, option_type="put")
        self.assertLess(g_put["delta"], 0.0)

    def test_generate_payoff_diagram_strategies(self):
        strategies = [
            "Bull Call Spread",
            "Bear Put Spread",
            "Iron Condor",
            "Long Straddle",
            "Long Strangle",
            "Covered Call",
            "Protective Put"
        ]
        for strat in strategies:
            fig, metrics = generate_payoff_diagram(spot_price=1000.0, strategy=strat, dte=30, iv=0.25)
            self.assertIsNotNone(fig)
            self.assertIsNotNone(metrics)
            self.assertEqual(metrics["strategy"], strat)
            self.assertIn("max_profit", metrics)
            self.assertIn("max_loss", metrics)
            self.assertIn("net_delta", metrics)
            self.assertIn("breakevens", metrics)

if __name__ == "__main__":
    unittest.main()
