import unittest
import pandas as pd
from analytics.options_greeks import calc_bs_greeks, enrich_options_chain_with_greeks

class TestOptionsGreeks(unittest.TestCase):
    def test_call_greeks(self):
        spot = 2500.0
        strike = 2500.0
        tte_years = 30.0 / 365.0
        iv = 0.20
        greeks = calc_bs_greeks(spot=spot, strike=strike, tte_years=tte_years, volatility=iv, is_call=True)

        # ATM Call delta should be around 0.50
        self.assertAlmostEqual(greeks["delta"], 0.50, delta=0.15)
        self.assertGreater(greeks["gamma"], 0.0)
        self.assertLess(greeks["theta"], 0.0)  # Time decay is negative
        self.assertGreater(greeks["vega"], 0.0)

    def test_put_greeks(self):
        spot = 2500.0
        strike = 2500.0
        tte_years = 30.0 / 365.0
        iv = 0.20
        greeks = calc_bs_greeks(spot=spot, strike=strike, tte_years=tte_years, volatility=iv, is_call=False)

        # ATM Put delta should be around -0.50
        self.assertAlmostEqual(greeks["delta"], -0.50, delta=0.15)
        self.assertGreater(greeks["gamma"], 0.0)
        self.assertLess(greeks["theta"], 0.0)
        self.assertGreater(greeks["vega"], 0.0)

    def test_enrich_options_chain(self):
        df_chain = pd.DataFrame({
            "Strike": [2400.0, 2500.0, 2600.0],
            "CE LTP": [120.0, 50.0, 15.0],
            "CE OI": [50000, 120000, 80000],
            "CE IV": [21.5, 20.0, 19.2],
            "PE LTP": [18.0, 48.0, 115.0],
            "PE OI": [70000, 95000, 40000],
            "PE IV": [22.0, 20.5, 20.0]
        })
        enriched = enrich_options_chain_with_greeks(df_chain, spot_price=2500.0, days_to_expiry=14)
        self.assertIn("CE Delta", enriched.columns)
        self.assertIn("CE Theta", enriched.columns)
        self.assertIn("PE Delta", enriched.columns)
        self.assertIn("PE Theta", enriched.columns)
        self.assertEqual(len(enriched), 3)

if __name__ == "__main__":
    unittest.main()
