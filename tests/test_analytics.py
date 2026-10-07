import unittest
import pandas as pd
import numpy as np

from analytics.liquidity_sweep import detect_liquidity_sweeps
from analytics.volume_profile import calc_volume_profile
from analytics.pullback_ema import run_pullback_ema_backtest

class TestAnalyticsEngine(unittest.TestCase):
    def setUp(self):
        # Create a synthetic OHLCV dataset of 100 periods
        np.random.seed(42)
        dates = pd.date_range("2026-01-01", periods=100, freq="B")
        close_prices = 100.0 + np.cumsum(np.random.randn(100) * 1.5)
        high_prices = close_prices + np.random.uniform(0.5, 2.0, 100)
        low_prices = close_prices - np.random.uniform(0.5, 2.0, 100)
        open_prices = low_prices + np.random.uniform(0.1, 1.5, 100)
        volume = np.random.randint(10000, 500000, 100)

        self.df = pd.DataFrame({
            "Date": dates,
            "Open": open_prices,
            "High": high_prices,
            "Low": low_prices,
            "Close": close_prices,
            "Volume": volume
        })

    def test_volume_profile_calculation(self):
        profile_df, value_area = calc_volume_profile(self.df, price_bins=20)
        self.assertIsInstance(profile_df, pd.DataFrame)
        self.assertIn("price", profile_df.columns)
        self.assertIn("volume", profile_df.columns)
        self.assertEqual(len(profile_df), 20)
        
        va_low, va_high = value_area
        self.assertLess(va_low, va_high)

    def test_liquidity_sweep_detection(self):
        sweep_df = self.df.copy()
        sweep_df["timestamp"] = sweep_df["Date"]
        sweep_df["bid_volume"] = sweep_df["Volume"] * 0.4
        sweep_df["ask_volume"] = sweep_df["Volume"] * 0.6
        # Inject an outlier burst to trigger sweep
        sweep_df.loc[10, "bid_volume"] = sweep_df.loc[10, "Volume"] * 0.95

        sweeps = detect_liquidity_sweeps(sweep_df, sweep_threshold=0.01)
        self.assertIsInstance(sweeps, list)

    def test_pullback_ema_backtest(self):
        bt_df, trades, stats = run_pullback_ema_backtest(self.df, capital=100000.0)
        self.assertIsInstance(bt_df, pd.DataFrame)
        self.assertIsInstance(trades, list)
        self.assertIsInstance(stats, dict)

if __name__ == "__main__":
    unittest.main()
