import unittest
import os
import tempfile
import json

class TestBrokerCredentials(unittest.TestCase):
    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        os.environ["XERCES_DATA_DIR"] = self.temp_dir.name
        # Re-import or reload database module to point to temp dir
        import importlib
        import data.database as db
        self.db = importlib.reload(db)

    def tearDown(self):
        self.temp_dir.cleanup()
        os.environ.pop("XERCES_DATA_DIR", None)

    def test_save_and_load_credentials_dict(self):
        broker_name = "Kotak Neo (NSE/BSE)"
        creds = {
            "consumer_key": "test_key",
            "consumer_secret": "test_secret",
            "mobile_number": "9999999999",
            "client_code": "CL123"
        }
        self.db.save_broker_credentials(broker_name, creds)
        loaded = self.db.load_broker_credentials(broker_name)
        self.assertEqual(loaded["consumer_key"], "test_key")
        self.assertEqual(loaded["client_code"], "CL123")

    def test_save_and_load_credentials_json_string(self):
        broker_name = "Zerodha Kite Connect"
        creds = {
            "api_key": "kite_key_abc",
            "api_secret": "kite_sec_xyz"
        }
        # Passing JSON string directly should be safely handled
        self.db.save_broker_credentials(broker_name, json.dumps(creds))
        loaded = self.db.load_broker_credentials(broker_name)
        self.assertIsInstance(loaded, dict)
        self.assertEqual(loaded["api_key"], "kite_key_abc")

    def test_load_nonexistent_broker(self):
        loaded = self.db.load_broker_credentials("NonExistentBroker")
        self.assertEqual(loaded, {})

if __name__ == "__main__":
    unittest.main()
