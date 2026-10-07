import unittest
from brokers.kotak_neo import KotakNeoAdapter
from brokers.zerodha_kite import ZerodhaKiteAdapter
from brokers.alpaca import AlpacaUSAdapter
from brokers.executor import execute_order

class TestBrokerAdapters(unittest.TestCase):
    def test_kotak_neo_adapter(self):
        adapter = KotakNeoAdapter(consumer_key="TEST_KEY", mobile_number="9999999999", client_code="C123")
        auth = adapter.authenticate()
        self.assertEqual(auth["status"], "SUCCESS")
        
        order = adapter.place_order(symbol="RELIANCE.NS", transaction_type="BUY", quantity=10, price=2500.0, order_type="LMT")
        self.assertEqual(order["status"], "COMPLETE")
        self.assertEqual(order["symbol"], "RELIANCE")
        self.assertEqual(order["quantity"], 10)

        positions = adapter.get_positions()
        self.assertIsInstance(positions, list)
        self.assertTrue(len(positions) > 0)

    def test_zerodha_kite_adapter(self):
        adapter = ZerodhaKiteAdapter(api_key="KITE_TEST_KEY", api_secret="KITE_TEST_SEC")
        order = adapter.place_order(symbol="INFY.NS", transaction_type="BUY", quantity=15)
        self.assertEqual(order["status"], "COMPLETE")
        self.assertEqual(order["symbol"], "INFY")
        self.assertEqual(order["quantity"], 15)

        positions = adapter.get_positions()
        self.assertIsInstance(positions, list)
        self.assertTrue(len(positions) > 0)

    def test_alpaca_us_adapter(self):
        adapter = AlpacaUSAdapter(api_key="DEMO_KEY", secret_key="DEMO_SEC", paper=True)
        order = adapter.place_order(symbol="NVDA", transaction_type="BUY", quantity=5, price=125.0, order_type="limit")
        self.assertEqual(order["status"], "COMPLETE")
        self.assertEqual(order["symbol"], "NVDA")
        self.assertEqual(order["quantity"], 5)

        positions = adapter.get_positions()
        self.assertIsInstance(positions, list)
        self.assertTrue(len(positions) > 0)

    def test_executor_paper_trade(self):
        res = execute_order(
            broker_name="Kotak Neo (NSE/BSE)",
            symbol="TCS.NS",
            transaction_type="BUY",
            quantity=10,
            price=3900.0,
            order_type="LMT"
        )
        self.assertEqual(res["status"], "COMPLETE")
        self.assertTrue(res.get("paper_mode", False))
        self.assertTrue(res["order_id"].startswith("SIM_"))

if __name__ == "__main__":
    unittest.main()
