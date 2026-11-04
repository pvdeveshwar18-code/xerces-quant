import unittest
import pandas as pd
import numpy as np
import xerces_plus as xp

class TestReports(unittest.TestCase):
    def setUp(self):
        self.sample_ctx = {
            "ticker": "TATAMOTORS.NS",
            "name": "Tata Motors Ltd.",
            "price": 980.50,
            "change_1d": 1.75,
            "signal": "BUY",
            "strength": 82,
            "rsi": 62.4,
            "macd": 4.12,
            "macd_signal": 2.85,
            "sma20": 960.0,
            "sma50": 930.0,
            "sma200": 850.0,
            "atr": 18.4,
            "vol": 0.24,
            "hi52": 1065.0,
            "lo52": 615.0,
            "whale_net": 125000000.0,
            "whale_conviction": 68.5,
            "retail_conviction": 31.5,
            "flow_sentiment": "BULLISH ACCUMULATION",
            "flow_divergence": "BULLISH ACCUMULATION DIVERGENCE",
            "cmf_20": 0.18,
            "var_95_pct": 2.15,
            "cvar_95_pct": 3.42,
            "fundamentals": {
                "Market Cap (Cr)": 360000.0,
                "P/E Ratio": 14.8,
                "P/B Ratio": 3.2,
                "ROE (%)": 22.4,
            }
        }
        self.thesis_text = (
            "Setup: Strong institutional whale accumulation with positive MACD divergence.\n\n"
            "Entry: At CMP 980.50 with stop-loss at 952.90 (1.5x ATR buffer).\n\n"
            "Targets: T1 at 1025.00, T2 at 1065.00."
        )
        self.news_summary = "Tata Motors reports solid quarterly margin expansion across EV segments."

    def test_build_pdf_report(self):
        pdf_bytes = xp.build_pdf_report(self.sample_ctx, self.thesis_text, self.news_summary)
        self.assertIsInstance(pdf_bytes, bytes)
        self.assertGreater(len(pdf_bytes), 1000)
        self.assertTrue(pdf_bytes.startswith(b"%PDF-"))

    def test_build_html_tearsheet(self):
        html_str = xp.build_html_tearsheet(self.sample_ctx, self.thesis_text, self.news_summary)
        self.assertIsInstance(html_str, str)
        self.assertIn("<!DOCTYPE html>", html_str)
        self.assertIn("Tata Motors Ltd.", html_str)
        self.assertIn("TATAMOTORS.NS", html_str)
        self.assertIn("Whale Net Flow", html_str)
        self.assertIn("Tail Risk &amp; Expected Shortfall", html_str)
        self.assertIn("3.42%", html_str)
        self.assertIn("AI Quantitative Trade Thesis", html_str)

    def test_build_excel_bytes(self):
        sheets = {
            "OHLCV": pd.DataFrame({"Close": [100, 102, 105], "Volume": [1000, 1200, 1500]}),
            "Trades": pd.DataFrame({"Side": ["BUY"], "Price": [100], "PnL": [5.0]})
        }
        excel_bytes = xp.build_excel_bytes(sheets)
        self.assertIsInstance(excel_bytes, bytes)
        self.assertGreater(len(excel_bytes), 500)

if __name__ == "__main__":
    unittest.main()
