import streamlit as st
import time
import datetime
import pandas as pd

from ui.tabs.brokers import render_brokers_tab
from brokers.executor import execute_order, SUPPORTED_BROKERS


def render_login():
    """Render a lightweight login or logout button in the sidebar or menu."""
    if st.session_state.get("user"):
        st.info(f"Logged in as {st.session_state['user']['username']}")
        if st.button("Logout", key="toolbar_logout_btn"):
            st.session_state.pop("user", None)
            st.rerun()
        return

    with st.expander("👤 User Profile"):
        username = st.text_input("Username", key="toolbar_user_in")
        password = st.text_input("Password", type="password", key="toolbar_pw_in")
        if st.button("Sign In", key="toolbar_signin_btn"):
            st.session_state["user"] = {"username": username}
            st.success(f"Welcome, {username}!")
            st.rerun()


def render_order_history():
    """Display the order audit log persisted in SQLite with filtering and live refresh."""
    from utils import db

    col_h1, col_h2 = st.columns([1, 2])
    with col_h1:
        if st.button("🔄 Refresh Order History", key="refresh_order_history_btn"):
            st.rerun()
    with col_h2:
        filter_mode = st.radio(
            "Filter History:",
            ["All Records", "Paper Trading Only", "Live Orders Only"],
            horizontal=True,
            key="audit_filter_mode"
        )

    audit_entries = db.get_audit_entries(limit=500)
    if not audit_entries:
        st.info("No order activity recorded in the SQLite audit log yet.")
        return

    rows = []
    for entry in audit_entries:
        is_paper = bool(entry.get("paper_mode", False))
        if filter_mode == "Paper Trading Only" and not is_paper:
            continue
        if filter_mode == "Live Orders Only" and is_paper:
            continue

        ts = entry.get("timestamp", 0)
        dt_str = datetime.datetime.fromtimestamp(ts).strftime("%Y-%m-%d %H:%M:%S") if ts else "N/A"
        req = entry.get("request", {})
        resp = entry.get("response", {})

        rows.append({
            "Time": dt_str,
            "Mode": "🟢 PAPER" if is_paper else "🔴 LIVE",
            "Broker": req.get("broker_name", "-"),
            "Symbol": req.get("symbol", "-"),
            "Side": req.get("transaction_type", "-"),
            "Qty": req.get("quantity", "-"),
            "Price (₹)": req.get("price", "-"),
            "Type": req.get("order_type", "-"),
            "Status": resp.get("status", "COMPLETE"),
            "Order ID": resp.get("order_id", "-"),
            "Message": resp.get("message", "-"),
        })

    if not rows:
        st.info(f"No records matching filter '{filter_mode}'.")
        return

    df_history = pd.DataFrame(rows)
    st.dataframe(df_history, use_container_width=True, hide_index=True)


def render_order_tab(selected_name: str, selected_ticker: str, close: float):
    """Unified Order Execution, Audit History, and Broker Configuration Tab."""
    st.markdown(f'<p class="section-header">[ 🛒 ORDER TERMINAL & BROKER DESK — {selected_name} ]</p>', unsafe_allow_html=True)

    tab_exec, tab_hist, tab_brk = st.tabs([
        "⚡ 1-Click Order Execution",
        "📜 Executed Order History & SQLite Audit Log",
        "🔌 Broker Accounts & Live WebSockets"
    ])

    with tab_exec:
        paper_mode = st.session_state.get("paper_mode", st.session_state.get("config", {}).get("PAPER_MODE", True))
        mode_badge = "🟢 PAPER TRADING (SIMULATION)" if paper_mode else "🔴 LIVE REAL BROKER EXECUTION"
        mode_color = "#00e87a" if paper_mode else "#ff3355"

        st.markdown(
            f"""<div class="glass-card" style="border-left:4px solid {mode_color};padding:8px 14px;margin-bottom:12px;">
                <span class="glass-label">CURRENT TRADING MODE</span>:
                <b style="color:{mode_color};font-family:'Space Mono',monospace;">{mode_badge}</b>
                <span style="font-size:11px;color:#8a99ad;margin-left:10px;">(Toggle in sidebar under Risk Controls)</span>
            </div>""",
            unsafe_allow_html=True
        )

        col_e1, col_e2, col_e3, col_e4 = st.columns([1.5, 1, 1, 1])
        with col_e1:
            exec_broker = st.selectbox("Broker Account:", SUPPORTED_BROKERS, index=0, key="exec_brk_tab")
        with col_e2:
            exec_action = st.selectbox("Order Side:", ["BUY", "SELL"], key="exec_side_tab")
        with col_e3:
            exec_product = st.selectbox("Product:", ["CNC (Delivery)", "MIS (Intraday)", "NRML (F&O)"], key="exec_prod_tab")
        with col_e4:
            exec_quantity = st.number_input("Shares Qty:", min_value=1, value=10, step=5, key="exec_qty_tab")

        col_p1, col_p2, col_p3 = st.columns([1, 1, 1])
        with col_p1:
            exec_order_type = st.radio("Order Type:", ["MARKET", "LIMIT"], horizontal=True, key="exec_type_tab")
        with col_p2:
            exec_price = st.number_input(
                "Order Price (₹):",
                min_value=0.01,
                value=round(close, 2) if close and close > 0 else 100.0,
                step=1.0,
                key="exec_px_tab"
            )
        with col_p3:
            est_val = exec_quantity * (exec_price if exec_order_type == "LIMIT" else (close or 0.0))
            st.markdown(
                f"""<div class="glass-card" style="padding:10px 14px;margin-top:4px;">
                    <p class="glass-label">ESTIMATED VALUE</p>
                    <div style="font-family:'Orbitron',sans-serif;font-size:1.1rem;color:#00c8ff;font-weight:700;">₹{est_val:,.2f}</div>
                </div>""",
                unsafe_allow_html=True
            )

        btn_label = f"🚀 EXECUTE {exec_action} ORDER NOW ({'PAPER' if paper_mode else 'LIVE'})"
        if st.button(btn_label, use_container_width=True, key="exec_now_tab_btn"):
            with st.spinner(f"Routing {exec_action} order for {selected_ticker} to {exec_broker}…"):
                res = execute_order(
                    broker_name=exec_broker,
                    symbol=selected_ticker,
                    transaction_type=exec_action,
                    quantity=exec_quantity,
                    price=exec_price,
                    order_type="LMT" if exec_order_type == "LIMIT" else "MKT"
                )
                st.success(f"✅ {res.get('message', 'Order placed successfully')}")
                st.info(f"Order ID: `{res.get('order_id', '-')}` | Status: `{res.get('status', 'COMPLETE')}` | Broker: `{res.get('broker', exec_broker)}`")

    with tab_hist:
        render_order_history()

    with tab_brk:
        render_brokers_tab(selected_name=selected_name, selected_ticker=selected_ticker, close=close)
