import unittest
import os
import tempfile
import time
from utils.db import init_db, add_audit_entry, get_audit_entries, _sanitize_data

class TestAuditDB(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.db_path = os.path.join(self.temp_dir.name, "test_audit.db")

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_init_and_empty_entries(self):
        init_db(self.db_path)
        entries = get_audit_entries(db_path=self.db_path)
        self.assertEqual(entries, [])

    def test_sanitize_sensitive_keys(self):
        payload = {
            "api_key": "secret_key_12345",
            "access_token": "token_abcde",
            "password": "supersecretpassword",
            "symbol": "RELIANCE",
            "quantity": 10
        }
        sanitized = _sanitize_data(payload)
        self.assertEqual(sanitized["symbol"], "RELIANCE")
        self.assertEqual(sanitized["quantity"], 10)
        self.assertTrue(sanitized["api_key"].startswith("***"))
        self.assertTrue(sanitized["access_token"].startswith("***"))
        self.assertTrue(sanitized["password"].startswith("***"))

    def test_add_and_get_audit_entry(self):
        init_db(self.db_path)
        entry = {
            "timestamp": time.time(),
            "paper_mode": True,
            "request": {
                "broker_name": "Kotak Neo (NSE/BSE)",
                "symbol": "TCS",
                "transaction_type": "BUY",
                "quantity": 5,
                "price": 3950.0,
                "order_type": "LMT"
            },
            "response": {
                "status": "COMPLETE",
                "order_id": "TEST_ORD_001",
                "message": "Simulated order filled"
            }
        }
        add_audit_entry(entry, db_path=self.db_path)

        entries = get_audit_entries(limit=10, db_path=self.db_path)
        self.assertEqual(len(entries), 1)
        retrieved = entries[0]
        self.assertTrue(retrieved["paper_mode"])
        self.assertEqual(retrieved["request"]["symbol"], "TCS")
        self.assertEqual(retrieved["response"]["order_id"], "TEST_ORD_001")

if __name__ == "__main__":
    unittest.main()
