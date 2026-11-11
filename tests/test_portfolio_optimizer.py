import unittest
import numpy as np
import pandas as pd

from portfolio.optimizer import run_mean_variance_optimization, run_black_litterman_optimization
from engine.portfolio_exit import generate_exit_strategy
from analytics.indicators import add_indicators
from analytics.capital_flow import compute_capital_flow, compute_price_level_order_flow

class TestPortfolioAndOptimizers(unittest.TestCase):
    def setUp(self):
        np.random.seed(42)
        n = 100
        dates = pd.date_range("2026-01-01", periods=n, freq="B")
        self.returns_df = pd.DataFrame({
            "RELIANCE": np.random.normal(0.001, 0.015, n),
            "TCS": np.random.normal(0.0008, 0.012, n),
            "INFY": np.random.normal(0.0012, 0.018, n),
        }, index=dates)

        # Synthetic OHLCV
        close = 1000.0 + np.cumsum(np.random.randn(n) * 10)
        self.ohlcv_df = pd.DataFrame({
            "Date": dates,
            "Open": close - 2.0,
            "High": close + 10.0,
            "Low": close - 10.0,
            "Close": close,
            "Volume": np.random.uniform(50000, 200000, size=n),
        })

    def test_mean_variance_optimization_sharpe(self):
        weights, ret, vol = run_mean_variance_optimization(
            tickers=["RELIANCE", "TCS", "INFY"],
            returns_matrix=self.returns_df,
            target="sharpe"
        )
        self.assertEqual(len(weights), 3)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=3)
        self.assertGreater(vol, 0.0)

    def test_mean_variance_optimization_min_vol(self):
        weights, ret, vol = run_mean_variance_optimization(
            tickers=["RELIANCE", "TCS", "INFY"],
            returns_matrix=self.returns_df,
            target="min_vol"
        )
        self.assertEqual(len(weights), 3)
        self.assertAlmostEqual(sum(weights.values()), 1.0, places=3)
        self.assertGreater(vol, 0.0)

    def test_portfolio_exit_strategy_with_uppercase_indicators(self):
        ind_df = add_indicators(self.ohlcv_df)
        plan = generate_exit_strategy(
            ticker="RELIANCE",
            entry_price=1000.0,
            quantity=50,
            current_price=1100.0,
            df=ind_df
        )
        self.assertIn("pnl", plan)
        self.assertIn("strategy_title", plan)
        self.assertIn("tranches", plan)
        self.assertGreater(len(plan["tranches"]), 0)

    def test_capital_flow_vectorized_invariants(self):
        flow = compute_capital_flow(self.ohlcv_df)
        self.assertIn("summary", flow)
        self.assertIn("price_levels", flow)
        self.assertFalse(flow["price_levels"].empty)
        # POC must be present
        self.assertEqual(flow["price_levels"]["is_poc"].sum(), 1)
        # Inflows and Outflows must be non-negative
        self.assertTrue((flow["price_levels"]["inflow"] >= 0).all())
        self.assertTrue((flow["price_levels"]["outflow"] >= 0).all())

if __name__ == "__main__":
    unittest.main()
