import streamlit as st
import time
import pandas as pd

from ui.tabs.brokers import render_brokers_tab
from ui.tabs.portfolio import render_portfolio_tab
from analytics.indicators import add_indicators, get_signal, get_signal_strength
from utils import credentials as cred
from brokers.executor import execute_order


def render_login():
    """Render a login modal or logout button in the sidebar dropdown selection."""
    if st.session_state.get("user"):
        st.info(f"Logged in as {st.session_state['user']['username']}")
        if st.button("Logout"):
            st.session_state.pop("user", None)
            st.experimental_rerun()
        return
    # Show modal for login
    with st.modal("Login"):
        st.markdown("## 📥 Login")
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        if st.button("Sign In"):
            st.session_state["user"] = {"username": username}
            st.success(f"Welcome, {username}!")
            st.experimental_rerun()


def render_order_history():
    """Display the order audit log stored in session_state."""
    audit = st.session_state.get("order_audit_log", [])
    if not audit:
        st.info("No order activity recorded yet.")
        return
    df = pd.DataFrame(audit)
    if "request" in df.columns:
        request_df = pd.json_normalize(df["request"]).add_prefix("req_")
        df = df.drop(columns=["request"]).reset_index(drop=True)
        df = pd.concat([df, request_df], axis=1)
    if "response" in df.columns:
        response_df = pd.json_normalize(df["response"]).add_prefix("res_")
        df = df.drop(columns=["response"]).reset_index(drop=True)
        df = pd.concat([df, response_df], axis=1)
    st.dataframe(df, use_container_width=True, hide_index=True)


def render_order_tab(selected_name: str, selected_ticker: str, close: float):
    """Unified Order UI – similar to the former Brokers tab order section."""
    st.markdown(f"#### ⚡ 1‑Click Order Execution — `{selected_name}` (`{selected_ticker}`)")
    col_e1, col_e2, col_e3, col_e4 = st.columns([1.5, 1, 1, 1])
    with col_e1:
        exec_broker = st.selectbox("Active Broker Account:", [
            "Kotak Neo (NSE/BSE)",
            "Zerodha Kite Connect",
            "Angel One SmartAPI",
            "Upstox Developer API",
            "Alpaca US Trading",
        ], index=0, key="exec_brk_tab")
    with col_e2:
        exec_action = st.selectbox("Order Side:", ["BUY", "SELL"], key="exec_side_tab")
    with col_e3:
        exec_product = st.selectbox("Product:", ["CNC (Delivery)", "MIS (Intraday)", "NRML (F&O)"], key="exec_prod_tab")
    with col_e4:
        exec_quantity = st.number_input("Shares Qty:", min_value=1, value=10, step=5, key="exec_qty_tab")

    col_p1, col_p2 = st.columns(2)
    with col_p1:
        exec_order_type = st.radio("Order Type:", ["MARKET", "LIMIT"], horizontal=True, key="exec_type_tab")
    with col_p2:
        exec_price = st.number_input(
            "Limit Price:", min_value=0.01, value=round(close, 2), step=1.0, key="exec_px_tab"
        )

    if st.button(f"🚀 EXECUTE {exec_action} ORDER NOW", use_container_width=True, key="exec_now_tab_btn"):
        with st.spinner(f"Routing {exec_action} order to {exec_broker}…"):
            creds = {
                "consumer_key": st.session_state.get("neo_key", ""),
                "consumer_secret": st.session_state.get("neo_secret", ""),
                "mobile_number": st.session_state.get("neo_mobile", ""),
                "client_code": st.session_state.get("neo_code", ""),
            }
            res = execute_order(
                broker_name=exec_broker,
                symbol=selected_ticker,
                transaction_type=exec_action,
                quantity=exec_quantity,
                price=exec_price,
                order_type="LMT" if exec_order_type == "LIMIT" else "MKT",
                credentials=creds,
            )
            st.success(f"✅ {res.get('message', 'Order processed')}")
            st.session_state.setdefault("order_audit_log", []).append({
                "timestamp": time.time(),
                "paper_mode": res.get("paper_mode", False),
                "request": {
                    "broker_name": exec_broker,
                    "symbol": selected_ticker,
                    "transaction_type": exec_action,
                    "quantity": exec_quantity,
                    "price": exec_price,
                    "order_type": exec_order_type,
                    "credentials": creds,
                },
                "response": res,
            })
            st.session_state.setdefault("order_history", []).append(res)
    st.markdown("---")
    st.markdown('#### 📜 Executed Order History & Audit Log')
    if st.session_state.get("order_history"):
        st.dataframe(pd.DataFrame(st.session_state["order_history"]), use_container_width=True, hide_index=True)
    else:
        st.info("No orders executed in this session yet.")
