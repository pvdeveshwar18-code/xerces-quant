import json
import os
import time
from utils import credentials as cred
from brokers.kotak_neo import KotakNeoAdapter
from brokers.zerodha_kite import ZerodhaKiteAdapter
from brokers.alpaca import AlpacaUSAdapter
from brokers.executor import _resolve_broker_credentials

def fetch_broker_portfolio(broker_name: str = "Kotak Neo (NSE/BSE)", force_refresh: bool = False):
    """Fetch user portfolio from selected broker adapter.

    Returns a list of dicts with keys:
        - symbol
        - quantity
        - avg_price
        - last_price
        - market_value
    """
    import streamlit as st

    safe_name = broker_name.replace(" ", "_").replace("(", "").replace(")", "").replace("/", "_").lower()
    cache_key = f"{safe_name}_portfolio"
    cache_ts_key = f"{safe_name}_portfolio_ts"
    cache_file = os.path.join(os.getcwd(), f".{safe_name}_cache.json")

    # Load persisted cache if present and fresh (< 5 mins)
    if not force_refresh and cache_key in st.session_state:
        if time.time() - st.session_state.get(cache_ts_key, 0) < 300:
            return st.session_state[cache_key]

    if os.path.exists(cache_file) and not force_refresh:
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                data = json.load(f)
            ts = data.get("_ts", 0)
            if time.time() - ts < 300:
                st.session_state[cache_key] = data.get("portfolio", [])
                st.session_state[cache_ts_key] = ts
                return st.session_state[cache_key]
        except Exception:
            pass

    # Resolve credentials via unified executor resolver
    creds_dict = _resolve_broker_credentials(broker_name)

    raw_positions = []
    if "Kotak Neo" in broker_name:
        adapter = KotakNeoAdapter(
            consumer_key=creds_dict.get("consumer_key", ""),
            consumer_secret=creds_dict.get("consumer_secret", ""),
            mobile_number=creds_dict.get("mobile_number", ""),
            client_code=creds_dict.get("client_code", "")
        )
        raw_positions = adapter.get_positions()
    elif "Zerodha" in broker_name:
        adapter = ZerodhaKiteAdapter(
            api_key=creds_dict.get("api_key", ""),
            api_secret=creds_dict.get("api_secret", ""),
            access_token=creds_dict.get("access_token", "")
        )
        raw_positions = adapter.get_positions()
    elif "Alpaca" in broker_name:
        adapter = AlpacaUSAdapter(
            api_key=creds_dict.get("api_key", ""),
            secret_key=creds_dict.get("secret_key", ""),
            paper=True
        )
        raw_positions = adapter.get_positions()
    else:
        raw_positions = [
            {"symbol": "RELIANCE.NS", "quantity": 10, "avg_price": 2400.0, "last_price": 2500.0},
            {"symbol": "TCS.NS", "quantity": 5, "avg_price": 3800.0, "last_price": 3900.0},
        ]

    portfolio = []
    for p in raw_positions:
        symbol = p.get("symbol", "")
        qty = int(p.get("quantity", 0))
        avg = float(p.get("avg_price", 0.0))
        last = float(p.get("last_price", 0.0))
        portfolio.append({
            "symbol": symbol,
            "quantity": qty,
            "avg_price": avg,
            "last_price": last,
            "market_value": round(qty * last, 2),
        })

    st.session_state[cache_key] = portfolio
    st.session_state[cache_ts_key] = time.time()
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({"_ts": st.session_state[cache_ts_key], "portfolio": portfolio}, f)
    except Exception:
        pass

    return portfolio

def fetch_kotak_portfolio(force_refresh: bool = False):
    """Backward-compatible helper for fetching Kotak Neo holdings."""
    return fetch_broker_portfolio(broker_name="Kotak Neo (NSE/BSE)", force_refresh=force_refresh)
