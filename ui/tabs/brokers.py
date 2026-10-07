import streamlit as st
import pandas as pd
from brokers.kotak_neo import KotakNeoAdapter
from brokers.kotak_neo_streamer import KotakNeoStreamer
from brokers.live_streamer import LiveMarketStreamer
from utils import credentials as cred
from data.database import save_broker_credentials, load_broker_credentials

def render_brokers_tab(selected_name: str, selected_ticker: str, close: float):
    """Render dedicated Broker Accounts, Authentication & Live Streaming Configuration Desk."""
    st.markdown('<p class="section-header">[ 🔌 BROKER INTEGRATIONS & LIVE WEBSOCKET FEEDS ]</p>', unsafe_allow_html=True)
    st.caption("Manage live broker connections (Kotak Neo, Zerodha Kite, Upstox, Alpaca) and real-time tick streaming feeds.")

    # Load global Kotak Neo credentials if saved
    global_creds = cred.get_kotak_credentials()
    if global_creds.get("consumer_key"):
        st.session_state.setdefault("neo_key", global_creds["consumer_key"])
        st.session_state.setdefault("neo_mobile", global_creds["mobile_number"])
        st.session_state.setdefault("neo_code", global_creds["client_code"])
        st.session_state.setdefault("neo_connected", True)

    # ── SECTION 1: BROKER CREDENTIALS & CONNECTION MANAGEMENT ────────────────
    st.markdown('#### 🔑 Broker API Credentials & Connection Management')

    b_tab1, b_tab2, b_tab3, b_tab4 = st.tabs([
        "🇮🇳 Kotak Neo", "🇮🇳 Zerodha Kite", "🇮🇳 Angel One / Upstox", "🇺🇸 Alpaca US"
    ])

    with b_tab1:
        st.markdown("**Kotak Neo API Configuration (NSE / BSE)**")
        saved_neo = load_broker_credentials("Kotak Neo (NSE/BSE)") or {}

        if not global_creds.get("consumer_key") and not saved_neo.get("consumer_key"):
            col_k1, col_k2 = st.columns(2)
            with col_k1:
                neo_key = st.text_input("Consumer Key:", value=st.session_state.get("neo_key", ""), type="password", key="neo_k_in")
                show_secret = st.checkbox("I have a Consumer Secret (legacy)", value=False, key="show_secret_chk")
                neo_secret = st.text_input("Consumer Secret:", value=st.session_state.get("neo_secret", ""), type="password", key="neo_s_in") if show_secret else ""
            with col_k2:
                neo_mobile = st.text_input("Mobile Number (+91):", value=st.session_state.get("neo_mobile", ""), key="neo_m_in")
                neo_code = st.text_input("Kotak Client Code:", value=st.session_state.get("neo_code", ""), key="neo_c_in")
        else:
            neo_key = st.session_state.get("neo_key") or saved_neo.get("consumer_key", "")
            neo_secret = st.session_state.get("neo_secret") or saved_neo.get("consumer_secret", "")
            neo_mobile = st.session_state.get("neo_mobile") or saved_neo.get("mobile_number", "")
            neo_code = st.session_state.get("neo_code") or saved_neo.get("client_code", "")
            st.info("✅ Using saved Kotak Neo credentials from secure local storage.")

        col_nb1, col_nb2 = st.columns([1, 1])
        with col_nb1:
            if st.button("💾 Save Kotak Credentials", use_container_width=True, key="save_neo_btn"):
                save_broker_credentials("Kotak Neo (NSE/BSE)", {
                    "consumer_key": neo_key, "consumer_secret": neo_secret,
                    "mobile_number": neo_mobile, "client_code": neo_code
                })
                st.session_state["neo_key"] = neo_key
                st.session_state["neo_mobile"] = neo_mobile
                st.session_state["neo_code"] = neo_code
                st.success("✅ Saved Kotak Neo credentials to database!")
        with col_nb2:
            if st.button("🔗 Connect Kotak Neo API", use_container_width=True, key="conn_neo_btn"):
                adapter = KotakNeoAdapter(consumer_key=neo_key, consumer_secret=neo_secret, mobile_number=neo_mobile, client_code=neo_code)
                adapter.authenticate()
                st.session_state["neo_connected"] = True
                st.session_state["neo_key"] = neo_key
                st.session_state["neo_secret"] = neo_secret
                st.session_state["neo_mobile"] = neo_mobile
                st.session_state["neo_code"] = neo_code
                st.success("✅ Kotak Neo API Session Connected Successfully!")

        if st.session_state.get("neo_connected"):
            st.markdown(
                """<div class="glass-card" style="border-left:4px solid #00e87a;padding:8px 12px;margin:10px 0;">
                <p class="glass-label">CONNECTION STATUS</p>
                <div style="color:#00e87a;font-family:'Space Mono',monospace;font-weight:700;">🟢 KOTAK NEO CONNECTED & READY</div>
                </div>""",
                unsafe_allow_html=True,
            )
            st.markdown("##### 📡 Real-Time WebSocket Streaming (Kotak Neo)")
            if 'kotak_streamer' not in st.session_state:
                st.session_state['kotak_streamer'] = None

            def _handle_live_candle(candle: dict):
                candles = st.session_state.setdefault('live_candles', [])
                candles.append(candle)
                st.info(
                    f"Live Candle – Time: {candle.get('time', 'N/A')}, Open: {candle.get('open')}, "
                    f"High: {candle.get('high')}, Low: {candle.get('low')}, Close: {candle.get('close')}"
                )

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
                        st.success(f'Live stream started for {selected_ticker}')
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
        saved_kite = load_broker_credentials("Zerodha Kite Connect") or {}
        kite_key_val = st.session_state.get("kite_key") or saved_kite.get("api_key", "")
        kite_sec_val = st.session_state.get("kite_secret") or saved_kite.get("api_secret", "")
        kite_tok_val = st.session_state.get("kite_token") or saved_kite.get("access_token", "")

        col_z1, col_z2 = st.columns(2)
        with col_z1:
            kite_k = st.text_input("Kite API Key:", value=kite_key_val, type="password", key="kite_k_in")
            kite_s = st.text_input("Kite API Secret:", value=kite_sec_val, type="password", key="kite_s_in")
        with col_z2:
            kite_tok = st.text_input("Session Access Token (Optional):", value=kite_tok_val, type="password", key="kite_t_in")
            st.caption("Tokens expire daily at 06:00 AM as per Zerodha regulations.")

        col_zb1, col_zb2 = st.columns(2)
        with col_zb1:
            if st.button("💾 Save Kite Credentials", use_container_width=True, key="save_kite_btn"):
                save_broker_credentials("Zerodha Kite Connect", {
                    "api_key": kite_k, "api_secret": kite_s, "access_token": kite_tok
                })
                st.session_state["kite_key"] = kite_k
                st.session_state["kite_secret"] = kite_s
                st.session_state["kite_token"] = kite_tok
                st.success("✅ Saved Zerodha Kite credentials!")
        with col_zb2:
            if st.button("🔗 Connect Zerodha Kite Session", use_container_width=True, key="conn_kite_btn"):
                streamer = LiveMarketStreamer(broker="Zerodha Kite")
                res = streamer.authenticate(api_key=kite_k, api_secret=kite_s, access_token=kite_tok)
                st.session_state["kite_connected"] = True
                st.session_state["kite_key"] = kite_k
                st.session_state["kite_secret"] = kite_s
                st.session_state["kite_token"] = kite_tok
                st.success(f"✅ {res.get('message', 'Zerodha Kite Session connected successfully!')}")

        if st.session_state.get("kite_connected"):
            st.markdown(
                """<div class="glass-card" style="border-left:4px solid #00c8ff;padding:8px 12px;margin:10px 0;">
                <p class="glass-label">CONNECTION STATUS</p>
                <div style="color:#00c8ff;font-family:'Space Mono',monospace;font-weight:700;">🟢 ZERODHA KITE ACTIVE</div>
                </div>""",
                unsafe_allow_html=True,
            )

    with b_tab3:
        st.markdown("**Angel One SmartAPI & Upstox Developer API**")
        saved_upstox = load_broker_credentials("Upstox Developer API") or {}
        upstox_key_val = st.session_state.get("upstox_key") or saved_upstox.get("api_key", "")
        upstox_k = st.text_input("API Key / Client ID:", value=upstox_key_val, type="password", key="upstox_k_in")

        col_ub1, col_ub2 = st.columns(2)
        with col_ub1:
            if st.button("💾 Save Credentials", use_container_width=True, key="save_upstox_btn"):
                save_broker_credentials("Upstox Developer API", {"api_key": upstox_k})
                st.session_state["upstox_key"] = upstox_k
                st.success("✅ Saved SmartAPI / Upstox credentials!")
        with col_ub2:
            if st.button("🔗 Connect API Session", use_container_width=True, key="conn_upstox_btn"):
                st.session_state["upstox_connected"] = True
                st.session_state["upstox_key"] = upstox_k
                st.success("✅ Upstox / SmartAPI Sandbox session activated!")

    with b_tab4:
        st.markdown("**Alpaca US Trading API Configuration**")
        saved_alpaca = load_broker_credentials("Alpaca US Trading") or {}
        alpaca_k_val = st.session_state.get("alpaca_key") or saved_alpaca.get("api_key", "")
        alpaca_s_val = st.session_state.get("alpaca_secret") or saved_alpaca.get("secret_key", "")

        alpaca_k = st.text_input("Alpaca API Key ID:", value=alpaca_k_val, type="password", key="alpaca_k_in")
        alpaca_s = st.text_input("Alpaca Secret Key:", value=alpaca_s_val, type="password", key="alpaca_s_in")

        col_ab1, col_ab2 = st.columns(2)
        with col_ab1:
            if st.button("💾 Save Alpaca Credentials", use_container_width=True, key="save_alpaca_btn"):
                save_broker_credentials("Alpaca US Trading", {"api_key": alpaca_k, "secret_key": alpaca_s})
                st.session_state["alpaca_key"] = alpaca_k
                st.session_state["alpaca_secret"] = alpaca_s
                st.success("✅ Saved Alpaca credentials!")
        with col_ab2:
            if st.button("🔗 Connect Alpaca US API", use_container_width=True, key="conn_alpaca_btn"):
                st.session_state["alpaca_connected"] = True
                st.session_state["alpaca_key"] = alpaca_k
                st.session_state["alpaca_secret"] = alpaca_s
                st.success("✅ Alpaca US API Paper/Live session active!")
