import json
import os
import time
from utils import credentials as cred
from brokers.kotak_neo import KotakNeoAdapter

def fetch_kotak_portfolio(force_refresh: bool = False):
    """Fetch the user's Kotak Neo portfolio.

    Returns a list of dicts with keys:
        - symbol
        - quantity
        - avg_price
        - last_price
        - market_value
    The function caches the result in ``st.session_state`` and optionally
    persists a JSON file (``.portfolio_cache.json``) in the workspace root.
    """
    import streamlit as st

    cache_key = "kotak_portfolio"
    cache_ts_key = "kotak_portfolio_ts"
    cache_file = os.path.join(os.getcwd(), ".portfolio_cache.json")

    # Load persisted cache if present and not stale
    if not force_refresh and cache_key in st.session_state:
        # fresh if < 5 minutes old
        if time.time() - st.session_state.get(cache_ts_key, 0) < 300:
            return st.session_state[cache_key]

    # Try loading from file (fallback if session lost)
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

    # --- Actual fetch from Kotak Neo ---
    creds = cred.get_kotak_credentials()
    adapter = KotakNeoAdapter(
        consumer_key=creds.get("consumer_key", ""),
        consumer_secret=creds.get("consumer_secret", ""),
        mobile_number=creds.get("mobile_number", ""),
        client_code=creds.get("client_code", "")
    )
    # Simulated: use adapter.get_positions() which currently returns []
    # In a real implementation this would call an endpoint like /portfolio/holdings
    raw_positions = adapter.get_positions()

    portfolio = []
    for p in raw_positions:
        # Expected dict keys: symbol, quantity, avg_price, last_price
        symbol = p.get("symbol", "")
        qty = p.get("quantity", 0)
        avg = p.get("avg_price", 0.0)
        last = p.get("last_price", 0.0)
        portfolio.append({
            "symbol": symbol,
            "quantity": qty,
            "avg_price": avg,
            "last_price": last,
            "market_value": qty * last,
        })

    # Cache in session and optionally write to file
    st.session_state[cache_key] = portfolio
    st.session_state[cache_ts_key] = time.time()
    try:
        with open(cache_file, "w", encoding="utf-8") as f:
            json.dump({"_ts": st.session_state[cache_ts_key], "portfolio": portfolio}, f)
    except Exception:
        pass

    return portfolio
