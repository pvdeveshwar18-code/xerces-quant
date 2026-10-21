import unittest
import numpy as np
import pandas as pd
from analytics.strategy_bot import evaluate_live_strategy_signal, deploy_strategy_signal

class TestStrategyBot(unittest.TestCase):
    def setUp(self):
        np.random.seed(42)
        n = 50
        dates = pd.date_range("2026-01-01", periods=n, freq="D")
        closes = np.linspace(100, 200, n)
        highs = closes + 2.0
        lows = closes - 2.0
        opens = closes - 0.5
        volumes = np.full(n, 10000.0)

        self.df = pd.DataFrame({
            "Date": dates,
            "Open": opens,
            "High": highs,
            "Low": lows,
            "Close": closes,
            "Volume": volumes,
            "SMA_20": closes - 5.0,
            "SMA_50": closes - 15.0,
            "ATR_14": np.full(n, 3.0),
            "RSI_14": np.full(n, 55.0),
        })

    def test_evaluate_insufficient_data(self):
        res = evaluate_live_strategy_signal(pd.DataFrame())
        self.assertEqual(res["status"], "INSUFFICIENT_DATA")
        self.assertEqual(res["action"], "HOLD")

    def test_evaluate_bullish_pullback(self):
        res = evaluate_live_strategy_signal(self.df, strategy_name="Pullback EMA")
        self.assertEqual(res["status"], "EVALUATED")
        self.assertEqual(res["action"], "BUY")
        self.assertGreater(res["strength"], 50)
        self.assertGreater(res["take_profit"], res["entry_price"])
        self.assertLess(res["stop_loss"], res["entry_price"])

    def test_deploy_strategy_signal_paper(self):
        res = deploy_strategy_signal(
            broker_name="Kotak Neo (NSE/BSE)",
            symbol="TCS.NS",
            action="BUY",
            quantity=5,
            price=3500.0,
            stop_loss=3400.0,
            take_profit=3700.0,
            paper_mode=True
        )
        self.assertIn("status", res)
        self.assertEqual(res["stop_loss"], 3400.0)
        self.assertEqual(res["take_profit"], 3700.0)

if __name__ == "__main__":
    unittest.main()
