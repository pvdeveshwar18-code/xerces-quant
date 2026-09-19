import streamlit as st
import pandas as pd
from brokers.executor import execute_order, SUPPORTED_BROKERS
from brokers.kotak_neo import KotakNeoAdapter
from brokers.kotak_neo_streamer import KotakNeoStreamer
from utils import credentials as cred

def render_brokers_tab(selected_name: str, selected_ticker: str, close: float):
    """Render dedicated Brokers & 1-Click Execution Tab."""
    st.markdown('<p class="section-header">[ 🔌 BROKER INTEGRATION & 1-CLICK TRADE EXECUTION ]</p>', unsafe_allow_html=True)
    st.caption("Manage live broker connections (Kotak Neo, Zerodha Kite, Upstox, Alpaca) and execute 1-click orders.")

    # Load global Kotak Neo credentials if saved
    global_creds = cred.get_kotak_credentials()
    if global_creds.get("consumer_key"):
        # Populate session state so the rest of the app sees the credentials
        st.session_state["neo_key"] = global_creds["consumer_key"]
        st.session_state["neo_secret"] = ""  # legacy secret not needed
        st.session_state["neo_mobile"] = global_creds["mobile_number"]
        st.session_state["neo_code"] = global_creds["client_code"]
        st.session_state["neo_connected"] = True

    # ── SECTION 1: BROKER CREDENTIALS & CONNECTION MANAGEMENT ────────────────
    st.markdown('#### 🔑 Broker API Credentials & Connection Management')

    b_tab1, b_tab2, b_tab3, b_tab4 = st.tabs([
        "🇮🇳 Kotak Neo", "🇮🇳 Zerodha Kite", "🇮🇳 Angel One / Upstox", "🇺🇸 Alpaca US"
    ])

    with b_tab1:
        st.markdown("**Kotak Neo API Configuration (NSE / BSE)**")
        if not global_creds.get("consumer_key"):
            # Show input fields for one‑off credential entry
            col_k1, col_k2 = st.columns(2)
            with col_k1:
                neo_key = st.text_input("Consumer Key:", value=st.session_state.get("neo_key", ""), type="password", key="neo_k_in")
                # Legacy secret optional – hidden unless user checks box
                show_secret = st.checkbox("I have a Consumer Secret (legacy)", value=False, key="show_secret_chk")
                if show_secret:
                    neo_secret = st.text_input("Consumer Secret:", value=st.session_state.get("neo_secret", ""), type="password", key="neo_s_in")
                else:
                    neo_secret = ""
            with col_k2:
                neo_mobile = st.text_input("Mobile Number (+91):", value=st.session_state.get("neo_mobile", ""), key="neo_m_in")
                neo_code = st.text_input("Kotak Client Code:", value=st.session_state.get("neo_code", ""), key="neo_c_in")
        else:
            # Use global credentials – hide inputs and just display status
            neo_key = st.session_state.get("neo_key", "")
            neo_secret = st.session_state.get("neo_secret", "")
            neo_mobile = st.session_state.get("neo_mobile", "")
            neo_code = st.session_state.get("neo_code", "")
            st.info("✅ Using globally saved Kotak Neo credentials.")
        if st.button("🔗 Connect Kotak Neo API", use_container_width=True, key="conn_neo_btn"):
            adapter = KotakNeoAdapter(consumer_key=neo_key, consumer_secret=neo_secret, mobile_number=neo_mobile, client_code=neo_code)
            auth_res = adapter.authenticate()
            st.session_state["neo_connected"] = True
            st.session_state["neo_key"] = neo_key
            st.session_state["neo_secret"] = neo_secret
            st.session_state["neo_mobile"] = neo_mobile
            st.session_state["neo_code"] = neo_code
            st.success("✅ Kotak Neo API Session Connected Successfully!")

        if st.session_state.get("neo_connected"):
            st.markdown(
                """
                <div class=\"glass-card\" style=\"border-left:4px solid #00e87a;\">\n                <p class=\"glass-label\">CONNECTION STATUS</p>\n                <div style=\"color:#00e87a;font-family:'Space Mono',monospace;font-weight:700;\">🟢 KOTAK NEO CONNECTED & READY</div>\n                </div>\n                """,
                unsafe_allow_html=True,
            )
            # Live Streamer Controls
            if 'kotak_streamer' not in st.session_state:
                st.session_state['kotak_streamer'] = None

            def _handle_live_candle(candle: dict):
                candles = st.session_state.get('live_candles', [])
                candles.append(candle)
                st.session_state['live_candles'] = candles
                st.info(
                    f"Live Candle – Time: {candle.get('time', 'N/A')}, Open: {candle.get('open')}, "
                    f"High: {candle.get('high')}, Low: {candle.get('low')}, Close: {candle.get('close')}"
                )

            if st.session_state.get('neo_connected'):
                col_start, col_stop = st.columns([1, 1])
                with col_start:
                    if st.button('▶️ Start Live Stream', key='start_stream'):
                        if st.session_state['kotak_streamer'] is None:
                            streamer = KotakNeoStreamer(
                                api_key=neo_key,
                                api_secret=neo_secret,
                                symbols=[selected_ticker],
                                on_candle=_handle_live_candle,
                                on_depth=None,
                            )
                            streamer.connect()
                            streamer.run()
                            st.session_state['kotak_streamer'] = streamer
                            st.success('Live stream started for ' + selected_ticker)
                        else:
                            st.warning('Streamer already running.')
                with col_stop:
                    if st.button('⏹ Stop Live Stream', key='stop_stream'):
                        if st.session_state['kotak_streamer'] is not None:
                            st.session_state['kotak_streamer'].stop()
                            st.session_state['kotak_streamer'] = None
                            st.success('Live stream stopped.')
                        else:
                            st.info('No active streamer to stop.')

    with b_tab2:
        st.markdown("**Zerodha Kite Connect Configuration**")
        st.text_input("Kite API Key:", type="password", key="kite_k_in")
        st.text_input("Kite API Secret:", type="password", key="kite_s_in")
        st.button("🔗 Connect Zerodha Kite", use_container_width=True, key="conn_kite_btn")

    with b_tab3:
        st.markdown("**Angel One SmartAPI & Upstox Developer API**")
        st.text_input("API Key / Client ID:", type="password", key="upstox_k_in")
        st.button("🔗 Connect API Session", use_container_width=True, key="conn_upstox_btn")

    with b_tab4:
        st.markdown("**Alpaca US Trading API Configuration**")
        st.text_input("Alpaca API Key ID:", type="password", key="alpaca_k_in")
        st.text_input("Alpaca Secret Key:", type="password", key="alpaca_s_in")
        st.button("🔗 Connect Alpaca US API", use_container_width=True, key="conn_alpaca_btn")

    st.markdown("---")

    # ── SECTION 2: 1-CLICK ORDER EXECUTION TERMINAL ─────────────────────────
    st.markdown(f'#### ⚡ 1-Click Order Execution Terminal — `{selected_name}` (`{selected_ticker}`)')

    col_e1, col_e2, col_e3, col_e4 = st.columns([1.5, 1, 1, 1])

    with col_e1:
        exec_broker = st.selectbox("Active Broker Account:", SUPPORTED_BROKERS, index=0, key="exec_brk_tab")
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
        exec_price = st.number_input(f"Limit Price:", min_value=0.01, value=round(close, 2), step=1.0, key="exec_px_tab")

    if st.button(f"🚀 EXECUTE {exec_action} ORDER NOW", use_container_width=True, key="exec_now_tab_btn"):
        with st.spinner(f"Routing {exec_action} order to {exec_broker}..."):
            creds = {
                "consumer_key": st.session_state.get("neo_key", ""),
                "consumer_secret": st.session_state.get("neo_secret", ""),
                "mobile_number": st.session_state.get("neo_mobile", ""),
                "client_code": st.session_state.get("neo_code", "")
            }
            res = execute_order(
                broker_name=exec_broker,
                symbol=selected_ticker,
                transaction_type=exec_action,
                quantity=exec_quantity,
                price=exec_price,
                order_type="LMT" if exec_order_type == "LIMIT" else "MKT",
                credentials=creds
            )
            st.success(f"✅ {res['message']}")
            if "order_history" not in st.session_state:
                st.session_state["order_history"] = []
            st.session_state["order_history"].append(res)

    # ── SECTION 3: RECENT ORDER EXECUTION LOGS ──────────────────────────────
    st.markdown("---")
    st.markdown('#### 📜 Executed Order History & Audit Log')
    if st.session_state.get("order_history"):
        st.dataframe(pd.DataFrame(st.session_state["order_history"]), use_container_width=True, hide_index=True)
    else:
        st.info("No orders executed in this session yet.")
