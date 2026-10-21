import unittest
import os
import tempfile
import time
import pandas as pd
from utils.db import init_db, add_audit_entry
from utils.journal import sync_audit_to_journal

class TestJournalSync(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_audit.db")
        init_db(self.db_path)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_sync_empty_audit_log(self):
        df = pd.DataFrame(columns=["Date", "Ticker", "Side", "Qty", "Entry", "Exit", "P&L (₹)", "P&L %", "Strategy", "Notes"])
        updated_df, count = sync_audit_to_journal(journal_df=df, db_path=self.db_path)
        self.assertEqual(count, 0)
        self.assertEqual(len(updated_df), 0)

    def test_sync_audit_entries_and_deduplication(self):
        entry1 = {
            "timestamp": time.time(),
            "paper_mode": True,
            "request": {
                "broker_name": "Zerodha Kite Connect",
                "symbol": "INFY.NS",
                "transaction_type": "BUY",
                "quantity": 25,
                "price": 1850.5,
            },
            "response": {
                "status": "COMPLETE",
                "order_id": "ORD_INFY_999",
            }
        }
        entry2 = {
            "timestamp": time.time(),
            "paper_mode": False,
            "request": {
                "broker_name": "Kotak Neo (NSE/BSE)",
                "symbol": "RELIANCE.BO",
                "transaction_type": "SELL",
                "quantity": 10,
                "price": 2980.0,
            },
            "response": {
                "status": "COMPLETE",
                "order_id": "ORD_REL_111",
            }
        }
        add_audit_entry(entry1, db_path=self.db_path)
        add_audit_entry(entry2, db_path=self.db_path)

        df = pd.DataFrame(columns=["Date", "Ticker", "Side", "Qty", "Entry", "Exit", "P&L (₹)", "P&L %", "Strategy", "Notes"])
        updated_df, count = sync_audit_to_journal(journal_df=df, db_path=self.db_path)

        self.assertEqual(count, 2)
        self.assertEqual(len(updated_df), 2)
        
        tickers = set(updated_df["Ticker"].tolist())
        self.assertIn("INFY", tickers)
        self.assertIn("RELIANCE", tickers)

        # Ensure deduplication: running sync again should yield 0 new entries
        updated_df2, count2 = sync_audit_to_journal(journal_df=updated_df, db_path=self.db_path)
        self.assertEqual(count2, 0)
        self.assertEqual(len(updated_df2), 2)

if __name__ == "__main__":
    unittest.main()
