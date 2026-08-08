"""
XERCES Sidebar UI Component
Contains risk parameters, chart toggles, backtest options, Watchlist management, and Price/RSI Alerts.
"""

import streamlit as st
import xerces_plus as xp

def render_sidebar(selected_ticker: str, selected_name: str):
    """
    Renders sidebar controls and returns configuration settings dictionary.
    """
    with st.sidebar:
        st.markdown("<p class='telemetry-tag' style='color:#00c8ff;font-weight:700;margin-bottom:5px;'>[ 🛡️ RISK CONTROLS ]</p>", unsafe_allow_html=True)
        allocated_capital = st.number_input("Capital Pool (₹)", min_value=1000, value=100000, step=5000)
        risk_per_trade    = st.slider("Risk per Trade (%)", 0.5, 5.0, 1.5, step=0.1)
        risk_reward       = st.slider("Risk:Reward (1:X)", 1.5, 4.0, 2.0, step=0.5)
        st.markdown("---")
        
        st.markdown("<p class='telemetry-tag' style='color:#00c8ff;font-weight:700;margin-bottom:5px;'>[ ⚙️ CHART SETTINGS ]</p>", unsafe_allow_html=True)
        show_tv_chart = st.checkbox("TradingView HTML5 Chart", value=False, help="Toggle responsive TradingView HTML5 Intraday chart component.")
        show_bb       = st.checkbox("Bollinger Bands", value=True)
        show_sma      = st.checkbox("SMA 20/50/200", value=True)
        show_vol      = st.checkbox("Volume bars", value=True)
        st.markdown("---")

        st.markdown("<p class='telemetry-tag' style='color:#00c8ff;font-weight:700;margin-bottom:5px;'>[ 📈 BACKTEST STRATEGY ]</p>", unsafe_allow_html=True)
        backtest_strategy = st.selectbox("Strategy", ["SMA Crossover", "RSI Mean Reversion", "Bollinger Bands Breakout", "MACD Crossover"])
        st.markdown("---")

        # ── ⭐ WATCHLIST ──
        st.markdown("<p class='telemetry-tag' style='color:#00c8ff;font-weight:700;margin-bottom:5px;'>[ ⭐ WATCHLIST ]</p>", unsafe_allow_html=True)
        _wl = xp.load_watchlist()
        if not selected_ticker.startswith("^"):
            _already = any(w["ticker"] == selected_ticker for w in _wl)
            if _already:
                if st.button(f"➖ Remove {selected_name}", use_container_width=True, key="wl_rm"):
                    xp.remove_from_watchlist(selected_ticker); st.rerun()
            else:
                if st.button(f"➕ Add {selected_name}", use_container_width=True, key="wl_add"):
                    xp.add_to_watchlist(selected_ticker, selected_name); st.rerun()
        def _load_watchlist_pick():
            _pick = st.session_state.get("wl_pick")
            if _pick and _pick != "Select":
                st.session_state["search_val"] = _pick

        if _wl:
            _wl_names = [f"{w['name']}" for w in _wl]
            _options = ["Select"] + _wl_names
            if st.session_state.get("wl_pick") not in _options:
                st.session_state["wl_pick"] = "Select"
            st.selectbox("Jump to", _options, key="wl_pick", on_change=_load_watchlist_pick)
        else:
            st.caption("Empty - add stocks from any analysis view.")
        st.markdown("---")

        # ── 🚨 ALERTS ──
        st.markdown("<p class='telemetry-tag' style='color:#ff6b35;font-weight:700;margin-bottom:5px;'>[ 🚨 ALERTS & WEBHOOKS ]</p>", unsafe_allow_html=True)
        _alerts = xp.load_alerts()
        _active = [a for a in _alerts if not a.get("triggered")]
        _fired  = [a for a in _alerts if a.get("triggered")]
        st.caption(f"{len(_active)} active · {len(_fired)} triggered")
        with st.expander("➕ Add alert", expanded=False):
            _akind = st.radio("Type", ["price", "rsi"], horizontal=True, key="al_kind")
            _aop   = st.radio("Condition", [">", "<"], horizontal=True, key="al_op")
            _last_price = float(st.session_state.get("_stock_ctx", {}).get("price", 100.0))
            _aval  = st.number_input("Threshold", value=(_last_price if _akind=="price" else 30.0), key="al_val")
            if st.button("Set Alert", use_container_width=True, key="al_add"):
                xp.add_alert(selected_ticker, selected_name, _akind, _aop, _aval)
                st.success("Alert saved."); st.rerun()

        with st.expander("📡 Webhook & Telegram Settings", expanded=False):
            tg_token = st.text_input("Telegram Bot Token", value="", type="password", key="tg_tok")
            tg_chat  = st.text_input("Telegram Chat ID", value="", key="tg_chat")
            wh_url   = st.text_input("Webhook URL (Discord/Slack)", value="", key="wh_url")
            
            if st.button("🧪 Send Test Notification", use_container_width=True, key="test_notif"):
                from utils.notifications import AlertNotificationDispatcher
                res = AlertNotificationDispatcher.dispatch_alert(
                    alert_title="🧪 XERCES TEST NOTIFICATION",
                    alert_details={
                        "name": selected_name, "ticker": selected_ticker,
                        "price": float(st.session_state.get("_stock_ctx", {}).get("price", 100.0)),
                        "rsi": float(st.session_state.get("_stock_ctx", {}).get("rsi", 50.0)),
                        "ml_signal": "BUY", "confidence": 85,
                        "condition_desc": "Test Push Notification Dispatch"
                    },
                    telegram_token=tg_token, telegram_chat_id=tg_chat, webhook_url=wh_url
                )
                if any(v.get("success") for v in res.values()):
                    st.success("Test notification dispatched successfully!")
                else:
                    st.error("Notification failed. Verify credentials.")

        for _a in _alerts[-6:][::-1]:
            _clr = "#00e87a" if _a.get("triggered") else "#ffcc00"
            _tag = "🔔 FIRED" if _a.get("triggered") else "⏳"
            st.markdown(f"<div style='background:rgba(7,18,32,0.6);padding:6px 8px;border-radius:4px;"
                        f"border-left:3px solid {_clr};margin-bottom:4px;font-size:11px;color:#ddeeff;'>"
                        f"{_tag} <b>{_a['name']}</b> · {_a['kind'].upper()} {_a['op']} {_a['value']}"
                        f"</div>", unsafe_allow_html=True)
        if _fired and st.button("🧹 Clear triggered", use_container_width=True, key="al_clr"):
            xp.save_alerts([a for a in _alerts if not a.get("triggered")]); st.rerun()
        st.markdown("---")


        # ── COMMAND HUB NAVIGATION ──
        st.markdown("<p class='section-header'>[ 🏛️ COMMAND HUBS ]</p>", unsafe_allow_html=True)
        selected_hub = st.radio(
            "Select Command Hub",
            [
                "🏛️ 0. Macro Overview Dashboard",
                "🎯 1. Decision & Signal Engine",
                "🛡️ 2. Portfolio & Risk Management",
                "📊 3. Deep Analytics & Forecasting",
                "📡 4. Market Intelligence",
                "📓 5. Trader Workspace & Exports"
            ],
            index=0
        )
        st.caption("⚠️ Not SEBI registered. Statistical analysis only. Not financial advice.")

    return {
        "allocated_capital": allocated_capital,
        "risk_per_trade": risk_per_trade,
        "risk_reward": risk_reward,
        "show_tv_chart": show_tv_chart,
        "show_bb": show_bb,
        "show_sma": show_sma,
        "show_vol": show_vol,
        "backtest_strategy": backtest_strategy,
        "selected_hub": selected_hub
    }
