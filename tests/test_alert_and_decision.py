import unittest
import numpy as np
import pandas as pd

from data.database import save_notification_config, load_notification_config
from notifications.alert_dispatcher import AlertDispatcher
from decision.engine import compute_decision
from analytics.indicators import add_indicators
from ai.committee import run_investment_committee

class TestAlertAndDecisionEngines(unittest.TestCase):
    def setUp(self):
        np.random.seed(42)
        n = 100
        dates = pd.date_range("2026-01-01", periods=n, freq="B")
        close = 1000.0 + np.cumsum(np.random.randn(n) * 10)
        self.df = pd.DataFrame({
            "Date": dates,
            "Open": close - 2.0,
            "High": close + 10.0,
            "Low": close - 10.0,
            "Close": close,
            "Volume": np.random.uniform(10000, 50000, size=n),
        })
        self.df = add_indicators(self.df)

    def test_notification_config_persistence(self):
        test_cfg = {
            "telegram_bot_token": "TEST_TOKEN_123",
            "telegram_chat_id": "999888777",
            "discord_webhook_url": "https://discord.com/api/webhooks/test"
        }
        save_notification_config(test_cfg)
        loaded = load_notification_config()
        self.assertEqual(loaded.get("telegram_bot_token"), "TEST_TOKEN_123")
        self.assertEqual(loaded.get("telegram_chat_id"), "999888777")
        self.assertEqual(loaded.get("discord_webhook_url"), "https://discord.com/api/webhooks/test")

    def test_alert_dispatcher_auto_load(self):
        test_cfg = {
            "telegram_bot_token": "TEST_TOKEN_123",
            "telegram_chat_id": "999888777",
            "discord_webhook_url": "https://discord.com/api/webhooks/test"
        }
        save_notification_config(test_cfg)
        dispatcher = AlertDispatcher()
        self.assertEqual(dispatcher.telegram_bot_token, "TEST_TOKEN_123")
        self.assertEqual(dispatcher.telegram_chat_id, "999888777")
        self.assertEqual(dispatcher.discord_webhook_url, "https://discord.com/api/webhooks/test")

    def test_alert_dispatcher_price_alert_format(self):
        dispatcher = AlertDispatcher(telegram_bot_token="", telegram_chat_id="", discord_webhook_url="")
        # Should gracefully return False without crashing when credentials are blank
        res = dispatcher.dispatch_price_alert({
            "name": "RELIANCE",
            "kind": "price",
            "op": ">",
            "value": 2500.0,
            "last_val": 2520.0
        })
        self.assertFalse(res)

    def test_compute_decision_scoring_and_breakdown(self):
        res = compute_decision(self.df, risk_reward=2.0)
        self.assertIn("score", res)
        self.assertIn("recommendation", res)
        self.assertIn("confidence", res)
        self.assertIn("breakdown", res)
        self.assertIn("entry", res)
        self.assertIn("stop", res)
        self.assertIn("targets", res)

        bd = res["breakdown"]
        for factor in ["trend", "momentum", "forecast", "mtf", "sentiment"]:
            self.assertIn(factor, bd)
            self.assertGreaterEqual(bd[factor], 0)

        # Score must be bounded [0, 100]
        self.assertTrue(0 <= res["score"] <= 100)
        self.assertTrue(0 <= res["confidence"] <= 100)

    def test_ai_investment_committee_prompt_structure(self):
        ctx = {
            "name": "Reliance Industries",
            "ticker": "RELIANCE.NS",
            "price": 2500.0,
            "change_1d": 1.25,
            "rsi": 55.0,
            "signal": "BUY",
            "strength": 75
        }
        # Model 'none' or offline should return guidance without unhandled exception
        result = run_investment_committee(ctx, model="auto")
        self.assertIsInstance(result, str)
        self.assertGreater(len(result), 0)

if __name__ == "__main__":
    unittest.main()
