import unittest
import numpy as np
import pandas as pd
from analytics.capital_flow import compute_capital_flow

class TestCapitalFlow(unittest.TestCase):
    def setUp(self):
        np.random.seed(42)
        n = 50
        dates = pd.date_range("2026-01-01", periods=n, freq="D")
        closes = 1000.0 + np.cumsum(np.random.randn(n) * 10)
        highs = closes + np.random.uniform(5, 15, size=n)
        lows = closes - np.random.uniform(5, 15, size=n)
        opens = (highs + lows) / 2.0
        volumes = np.random.uniform(10000, 50000, size=n)

        self.df = pd.DataFrame({
            "Date": dates,
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": closes,
            "Volume": volumes
        })

    def test_empty_or_short_df(self):
        empty_res = compute_capital_flow(pd.DataFrame())
        self.assertEqual(empty_res, {})
        short_res = compute_capital_flow(self.df.iloc[:3])
        self.assertEqual(short_res, {})

    def test_compute_capital_flow_structure(self):
        res = compute_capital_flow(self.df)
        self.assertIn("summary", res)
        self.assertIn("tiers", res)
        self.assertIn("divergence", res)
        self.assertIn("historical_flow_df", res)

        summary = res["summary"]
        self.assertIn("total_inflow", summary)
        self.assertIn("total_outflow", summary)
        self.assertIn("net_capital_flow", summary)
        self.assertIn("sentiment", summary)
        self.assertIn("cmf_20", summary)
        self.assertIn("mfi_14", summary)

        # Net flow = Inflow - Outflow
        expected_net = summary["total_inflow"] - summary["total_outflow"]
        self.assertAlmostEqual(summary["net_capital_flow"], expected_net, places=2)

    def test_order_size_tier_breakdown(self):
        res = compute_capital_flow(self.df)
        tiers = res["tiers"]
        expected_tiers = ["Extra-Large", "Large", "Medium", "Small"]
        for t in expected_tiers:
            self.assertIn(t, tiers)
            self.assertIn("inflow", tiers[t])
            self.assertIn("outflow", tiers[t])
            self.assertIn("net", tiers[t])
            self.assertIn("share_pct", tiers[t])

        # Total share % should sum to approx 100%
        total_share = sum(tiers[t]["share_pct"] for t in expected_tiers)
        self.assertAlmostEqual(total_share, 100.0, delta=1.0)

    def test_cumulative_columns(self):
        res = compute_capital_flow(self.df)
        hist = res["historical_flow_df"]
        self.assertIn("Cum_Net_Flow", hist.columns)
        self.assertIn("Cum_Smart_Money_Net", hist.columns)
        self.assertIn("Cum_Retail_Net", hist.columns)
        self.assertIn("CMF_20", hist.columns)
        self.assertIn("MFI_14", hist.columns)
        self.assertEqual(len(hist), len(self.df))

    def test_divergence_logic(self):
        # Create clear bullish divergence: price declines while strong lower wick hammer absorption occurs
        n = 30
        dates = pd.date_range("2026-01-01", periods=n, freq="D")
        closes = np.linspace(1000, 800, n)  # price declines 20%
        lows = closes - 25.0 # deep wick below
        highs = closes + 1.0  # closes at the absolute peak of the candle
        opens = closes - 1.0  # opens near close (hammer)
        volumes = np.full(n, 50000.0)

        bullish_df = pd.DataFrame({
            "Date": dates,
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": closes,
            "Volume": volumes
        })
        res = compute_capital_flow(bullish_df)
        div = res["divergence"]
        self.assertIn("BULLISH", div["type"])

if __name__ == "__main__":
    unittest.main()
