import datetime
import warnings
import pytz
import pandas as pd
import streamlit as st

import forecast_engine as fe
import xerces_plus as xp
from data.loader import (
    SECTORS, ALL_STOCKS, SYMBOL_ALIASES, COMMODITIES, COMMODITY_ALIASES, resolve_ticker, get_sector_peers,
    load_ohlcv, load_indices, fetch_news, fetch_fii_dii, parse_fii_dii,
    fetch_options_chain, parse_options_chain, fetch_fundamentals, load_intraday
)
from analytics.indicators import add_indicators, get_signal, get_signal_strength
from ui.layout import render_header, render_global_search, render_dashboard_landing
# Global configuration loading
import json, pathlib
CONFIG_PATH = pathlib.Path(__file__).parent / "config.json"
if CONFIG_PATH.is_file():
    with open(CONFIG_PATH) as _cfg_file:
        CONFIG = json.load(_cfg_file)
else:
    CONFIG = {}
st.session_state.setdefault("config", CONFIG)
from ui.tabs.chart import render_chart_tab
from ui.tabs.forecast import render_forecast_tab
from ui.tabs.backtest import render_backtest_tab
from ui.tabs.scanner import render_scanner_tab
from ui.tabs.risk import render_risk_tab
from ui.tabs.portfolio import render_portfolio_tab
from ui.tabs.fii_dii import render_fii_dii_tab
from ui.tabs.options import render_options_tab
from ui.tabs.fundamentals import render_fundamentals_tab
from ui.tabs.news import render_news_tab
from ui.tabs.heatmap import render_heatmap_tab
from ui.tabs.compare import render_compare_tab
from ui.tabs.ai_analyst import render_ai_analyst_tab
from ui.tabs.journal import render_journal_tab
from ui.tabs.export import render_export_tab
from ui.tabs.manual import render_manual_tab
from ui.toolbar import render_login, render_order_history, render_order_tab

warnings.filterwarnings("ignore")

# ══════════════════════════════════════════════════════════════════════════════
# PAGE CONFIG & STYLES
# ══════════════════════════════════════════════════════════════════════════════
st.set_page_config(page_title="XERCES // QUANT ENGINE", page_icon="⚡", layout="wide")
IST = pytz.timezone("Asia/Kolkata")

st.markdown("""
<style>
@import url('https://fonts.googleapis.com/css2?family=Orbitron:wght@400;600;800;900&family=Space+Mono&family=Inter:wght@300;400;500;600&display=swap');
html,body,[class*="css"]{font-family:'Inter',sans-serif;}
.stApp{background:radial-gradient(circle at 50% 0%,#0a192f 0%,#020813 100%) !important;color:#e2e8f0 !important;}
section[data-testid="stSidebar"]{background-color:rgba(3,11,24,0.97) !important;border-right:1px solid rgba(0,200,255,0.15) !important;}
.xerces-title{font-family:'Orbitron',sans-serif;font-weight:900;font-size:2.2rem;background:linear-gradient(90deg,#00c8ff,#00e87a);-webkit-background-clip:text;-webkit-text-fill-color:transparent;background-clip:text;letter-spacing:3px;margin:0;}
.telemetry-tag{font-family:'Space Mono',monospace;color:#4a7090;font-size:11px;letter-spacing:1px;}
.section-header{font-family:'Orbitron',sans-serif;color:#00c8ff;font-size:12px;letter-spacing:1px;margin-top:12px;margin-bottom:8px;}
.glass-card{background:rgba(7,18,32,0.65);border:1px solid rgba(0,200,255,0.15);border-radius:6px;padding:12px 16px;margin-bottom:10px;backdrop-filter:blur(4px);}
.glass-label{font-family:'Space Mono',monospace;color:#6a90aa;font-size:10px;margin:0;text-transform:uppercase;letter-spacing:1px;}
.glass-value{font-family:'Orbitron',sans-serif;font-size:1.3rem;font-weight:700;margin-top:2px;}
div[data-baseweb="tab-list"]{gap:3px;}
button[data-baseweb="tab"]{font-family:'Space Mono',monospace !important;border-radius:4px !important;background:rgba(10,25,40,0.4) !important;color:#5a80a0 !important;border:1px solid rgba(0,200,255,0.05) !important;padding:0.35rem 0.75rem !important;font-size:11px !important;}
button[data-baseweb="tab"][aria-selected="true"]{border-color:#00c8ff !important;color:#00c8ff !important;background:rgba(13,32,53,0.75) !important;}
.signal-buy{color:#00e87a;font-family:'Orbitron',sans-serif;font-weight:700;font-size:1.4rem;}
.signal-sell{color:#ff3355;font-family:'Orbitron',sans-serif;font-weight:700;font-size:1.4rem;}
.signal-hold{color:#ffcc00;font-family:'Orbitron',sans-serif;font-weight:700;font-size:1.4rem;}
.accuracy-good{color:#00e87a;font-weight:700;}
.accuracy-mid{color:#ffcc00;font-weight:700;}
.accuracy-bad{color:#ff3355;font-weight:700;}
div[data-testid="stRadio"] > div{flex-wrap:wrap;gap:4px;}
div[data-testid="stRadio"] label{background:rgba(10,25,40,0.4);border:1px solid rgba(0,200,255,0.08);border-radius:4px;padding:4px 8px;font-family:'Space Mono',monospace;font-size:10px;}
div[data-testid="stRadio"] label[data-checked="true"]{border-color:#00c8ff !important;color:#00c8ff !important;background:rgba(13,32,53,0.75) !important;}
</style>
""", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# MARKET HELPERS & FORECAST BUNDLE CACHING
# ══════════════════════════════════════════════════════════════════════════════
EST = pytz.timezone("America/New_York")

def get_market_now(market_mode: str = "Indian Market"):
    if "US" in market_mode:
        return datetime.datetime.now(EST)
    return datetime.datetime.now(IST)

def market_status(market_mode: str = "Indian Market"):
    now = get_market_now(market_mode)
    if "US" in market_mode:
        m_name = "NYSE"
    elif "Commodities" in market_mode:
        m_name = "MCX / COMEX"
    else:
        m_name = "NSE"

    if now.weekday() >= 5:
        return f"🔴 {m_name} CLOSED", "#ff3355"

    if "US" in market_mode:
        ot = now.replace(hour=9, minute=30, second=0, microsecond=0)
        ct = now.replace(hour=16, minute=0, second=0, microsecond=0)
    elif "Commodities" in market_mode:
        ot = now.replace(hour=9, minute=0, second=0, microsecond=0)
        ct = now.replace(hour=23, minute=30, second=0, microsecond=0)
    else:
        ot = now.replace(hour=9, minute=15, second=0, microsecond=0)
        ct = now.replace(hour=15, minute=30, second=0, microsecond=0)

    if ot <= now <= ct:
        return f"🟢 {m_name} OPEN", "#00e87a"
    return f"🔴 {m_name} CLOSED", "#ff3355"

@st.cache_data(ttl=1800, show_spinner=False)
def _cached_forecast_bundle(ticker: str, period: str, steps: int, holdout: int = 60):
    ohlcv = load_ohlcv(ticker, period=period)
    if ohlcv is None or len(ohlcv) < 60:
        return None
    s = ohlcv["Close"].astype(float).dropna()
    return fe.compute_forecast_bundle(s, steps=steps, holdout=holdout)

def run_backtest(df: pd.DataFrame, strategy: str):
    bt = df.copy().reset_index(drop=True)
    bt["Signal_BT"] = 0

    if strategy == "Institutional Confluence (Volume + ATR Stops)":
        from analytics.confluence import run_institutional_confluence_backtest
        bt_res, trades, summary = run_institutional_confluence_backtest(bt)
        buy_x = [t["Entry Date"] for t in trades]
        buy_y = [t["Entry ₹"] for t in trades]
        sell_x = [t["Exit Date"] for t in trades]
        sell_y = [t["Exit ₹"] for t in trades]
        return bt_res, trades, buy_x, buy_y, sell_x, sell_y

    if strategy == "PB EMA (Pullback to 20 EMA)":
        from analytics.pullback_ema import run_pullback_ema_backtest
        bt_res, trades, summary = run_pullback_ema_backtest(bt)
        buy_x = [t["Entry Date"] for t in trades]
        buy_y = [t["Entry ₹"] for t in trades]
        sell_x = [t["Exit Date"] for t in trades]
        sell_y = [t["Exit ₹"] for t in trades]
        return bt_res, trades, buy_x, buy_y, sell_x, sell_y

    from analytics.friction import calculate_indian_equity_friction

    if strategy == "SMA Crossover":
        valid = bt["SMA_20"].notna() & bt["SMA_50"].notna()
        bt.loc[valid & (bt["SMA_20"] > bt["SMA_50"]), "Signal_BT"] = 1
    elif strategy == "RSI Mean Reversion":
        sig, signals = 0, []
        for r in bt["RSI_14"].fillna(50):
            if r < 30: sig = 1
            elif r > 70: sig = 0
            signals.append(sig)
        bt["Signal_BT"] = signals
    elif strategy == "Bollinger Bands Breakout":
        sig, signals = 0, []
        for c, u, l in zip(bt["Close"].fillna(0), bt["BB_Upper"].fillna(0), bt["BB_Lower"].fillna(0)):
            if pd.isna(u) or pd.isna(l): signals.append(0); continue
            if c > u: sig = 1
            elif c < l: sig = 0
            signals.append(sig)
        bt["Signal_BT"] = signals
    elif strategy == "MACD Crossover":
        sig, signals = 0, []
        macd_vals = bt["MACD"].fillna(0).values
        macds_vals = bt["MACD_Signal"].fillna(0).values
        for i in range(len(bt)):
            if i == 0: signals.append(0); continue
            if macd_vals[i] > macds_vals[i] and macd_vals[i-1] <= macds_vals[i-1]: sig = 1
            elif macd_vals[i] < macds_vals[i] and macd_vals[i-1] >= macds_vals[i-1]: sig = 0
            signals.append(sig)
        bt["Signal_BT"] = signals

    bt["Position"] = bt["Signal_BT"].diff()
    trades, buy_x, buy_y, sell_x, sell_y = [], [], [], [], []
    in_trade, entry_price, entry_date = False, 0.0, None
    for idx in range(len(bt)):
        row = bt.iloc[idx]
        if row["Position"] == 1 and not in_trade and idx + 1 < len(bt):
            nxt = bt.iloc[idx + 1]
            in_trade, entry_price, entry_date = True, float(nxt["Open"]), nxt["Date"]
            buy_x.append(nxt["Date"])
            buy_y.append(float(nxt["Low"]) * 0.985 if pd.notna(nxt.get("Low")) else float(nxt["Open"]))
        elif row["Position"] == -1 and in_trade and idx + 1 < len(bt):
            nxt = bt.iloc[idx + 1]
            in_trade = False
            exit_p   = float(nxt["Open"])
            fric = calculate_indian_equity_friction(entry_price, exit_p, quantity=100)
            trades.append({
                "Entry Date": str(entry_date)[:10],
                "Exit Date": str(nxt["Date"])[:10],
                "Entry ₹": round(entry_price, 2),
                "Exit ₹": round(exit_p, 2),
                "Gross P&L %": fric["gross_pnl_pct"],
                "Friction & Tax ₹": fric["total_friction"],
                "Net P&L %": fric["net_pnl_pct"],
                "P&L %": fric["net_pnl_pct"],
                "Reason": "Indicator Signal Flip",
                "Result": "✅ WIN" if fric["net_pnl"] > 0 else "❌ LOSS"
            })
            sell_x.append(nxt["Date"])
            sell_y.append(float(nxt["High"]) * 1.015 if pd.notna(nxt.get("High")) else float(nxt["Open"]))
    return bt, trades, buy_x, buy_y, sell_x, sell_y

# ══════════════════════════════════════════════════════════════════════════════
# INITIALIZE FORECAST SESSION STATE
# ══════════════════════════════════════════════════════════════════════════════
if "fc_horizon_type" not in st.session_state:
    st.session_state["fc_horizon_type"] = "Swing Trade (Days)"
if "fc_steps" not in st.session_state:
    st.session_state["fc_steps"] = 60
if "fc_years" not in st.session_state:
    st.session_state["fc_years"] = 2
if "fc_history_period" not in st.session_state:
    st.session_state["fc_history_period"] = "2y"

# ══════════════════════════════════════════════════════════════════════════════
# HEADER & GLOBAL SEARCH
# ══════════════════════════════════════════════════════════════════════════════
market_mode = st.session_state.get("global_market_mode", "🇮🇳 Indian Market (NSE/BSE)")

now_dt = get_market_now(market_mode)
ms, mc = market_status(market_mode)
render_header(now_dt, ms, mc, market_mode=market_mode)
render_login()
search_raw = render_global_search(market_mode=market_mode)

# Ticker Resolution
search = search_raw.strip()
if "Commodities" in market_mode:
    default_index_sym = "GC=F"
    default_index_name = "GOLD (Continuous Futures)"
elif "US" in market_mode:
    default_index_sym = "^GSPC"
    default_index_name = "S&P 500"
else:
    default_index_sym = "^NSEI"
    default_index_name = "NIFTY 50"

selected_ticker, selected_name, is_dashboard = default_index_sym, default_index_name, True

if search:
    is_dashboard = False
    match_t, match_n = None, None
    sl = search.lower()
    su = search.upper()

    # 1. Check commodities
    if su in COMMODITY_ALIASES:
        match_t = COMMODITY_ALIASES[su]
        match_n = f"{su} Futures"
    else:
        for cat, items in COMMODITIES.items():
            for c_name, c_sym in items:
                if sl in c_name.lower() or su == c_sym.upper():
                    match_t, match_n = c_sym, c_name
                    break
            if match_t:
                break

    # 2. Check equities
    if not match_t:
        for label, ticker in ALL_STOCKS.items():
            if sl in label.lower():
                match_t, match_n = ticker, label.split(" (")[0]; break
        if not match_t:
            for label, ticker in ALL_STOCKS.items():
                sym = ticker.replace(".NS","").replace(".BO","")
                if sl.upper() == sym or sl.upper() == ticker.upper():
                    match_t, match_n = ticker, label.split(" (")[0]; break

    if match_t:
        selected_ticker, selected_name = match_t, match_n
    else:
        selected_ticker = resolve_ticker(search, market_mode=market_mode)
        selected_name   = search.upper().replace(".NS","").replace(".BO","").replace("=F","")

# Dashboard Landing Page
if is_dashboard:
    with st.spinner("Loading market indices..."):
        idx_data = load_indices(market_mode=market_mode)
    render_dashboard_landing(idx_data, market_mode=market_mode)
    st.stop()

# ══════════════════════════════════════════════════════════════════════════════
# SIDEBAR CONTROLS
# ══════════════════════════════════════════════════════════════════════════════
with st.sidebar:
    st.markdown("<p class='telemetry-tag' style='color:#00c8ff;font-weight:700;margin-bottom:5px;'>[ 🌍 TARGET MARKET ]</p>", unsafe_allow_html=True)
    market_mode = st.radio("Active Market:", ["🇮🇳 Indian Market (NSE/BSE)", "🛢️ Commodities (MCX / Global)", "🇺🇸 US Market (NASDAQ/NYSE)"], horizontal=True, key="global_market_mode")
    st.markdown("---")
    st.markdown("<p class='telemetry-tag' style='color:#00c8ff;font-weight:700;margin-bottom:5px;'>[ 🛡️ RISK CONTROLS ]</p>", unsafe_allow_html=True)
    allocated_capital = st.number_input("Capital Pool (₹)", min_value=1000, value=100000, step=5000)
    risk_per_trade    = st.slider("Risk per Trade (%)", 0.5, 5.0, 1.5, step=0.1)
    risk_reward       = st.slider("Risk:Reward (1:X)", 1.5, 4.0, 2.0, step=0.5)
    st.markdown("---")
    st.markdown("<p class='telemetry-tag' style='color:#00c8ff;font-weight:700;margin-bottom:5px;'>[ ⚙️ CHART SETTINGS ]</p>", unsafe_allow_html=True)
    show_bb   = st.checkbox("Bollinger Bands", value=True)
    show_sma  = st.checkbox("SMA 20/50/200", value=True)
    show_vol  = st.checkbox("Volume bars", value=True)
    st.markdown("---")
    st.markdown("<p class='telemetry-tag' style='color:#00c8ff;font-weight:700;margin-bottom:5px;'>[ 📈 BACKTEST STRATEGY ]</p>", unsafe_allow_html=True)
    backtest_strategy = st.selectbox("Strategy", [
        "Institutional Confluence (Volume + ATR Stops)",
        "PB EMA (Pullback to 20 EMA)",
        "SMA Crossover",
        "RSI Mean Reversion",
        "Bollinger Bands Breakout",
        "MACD Crossover"
    ])
    st.markdown("---")

    # Watchlist Sidebar
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
    if _wl:
        _pick = st.selectbox("Jump to", ["—"] + [f"{w['name']}" for w in _wl], key="wl_pick")
        if _pick != "—":
            _wt = next((w for w in _wl if w["name"] == _pick), None)
            if _wt:
                st.session_state["search_val"] = _wt["name"]
                st.info(f"Search '{_wt['name']}' above to load.")
        if st.button("🎯 Scan Watchlist Entry Hits", use_container_width=True, key="scan_wl_entry_btn"):
            with st.spinner("Scanning watchlist for entry point hits..."):
                from notifications.alert_dispatcher import AlertDispatcher
                dispatcher = AlertDispatcher()
                entry_hits = dispatcher.check_watchlist_entry_hits(_wl)
                if entry_hits:
                    st.success(f"🎯 {len(entry_hits)} Watchlist Entry Hits Detected!")
                    for hit in entry_hits:
                        st.info(f"**{hit['name']}** (`{hit['ticker']}`): Reached Entry Zone `{hit['entry_zone']}`. Target 1: `{hit['target_1']}`")
                else:
                    st.info("No watchlist stocks currently touching entry zones.")
    else:
        st.caption("Empty — add stocks from any analysis view.")
    st.markdown("---")

    # Alerts Sidebar
    st.markdown("<p class='telemetry-tag' style='color:#ff6b35;font-weight:700;margin-bottom:5px;'>[ 🚨 ALERTS ]</p>", unsafe_allow_html=True)
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
    st.caption("⚠️ Not SEBI registered. Statistical analysis only. Not financial advice. Data: Yahoo Finance.")

# ══════════════════════════════════════════════════════════════════════════════
# LOAD + VALIDATE DATA
# ══════════════════════════════════════════════════════════════════════════════
history_period = st.session_state.get("fc_history_period", "2y")
with st.spinner(f"Loading {selected_name} ({selected_ticker}) with {history_period} history..."):
    raw_df = load_ohlcv(selected_ticker, period=history_period)

if raw_df is None or len(raw_df) < 40:
    st.error(f"❌ Could not load data for **{selected_ticker}**.")
    if selected_ticker.endswith(".NS"):
        bse = selected_ticker.replace(".NS",".BO")
        st.info(f"Try BSE: type `{bse.replace('.BO','')} .BO` in the search bar, or verify the symbol on NSE India.")
    else:
        st.info("For NSE stocks append `.NS` (e.g. RELIANCE.NS). For BSE append `.BO`.")
    st.stop()

_df_cache_key = f"df__{selected_ticker}__{history_period}"
_bt_cache_key = f"bt__{selected_ticker}__{backtest_strategy}__{history_period}"

if _df_cache_key not in st.session_state:
    st.session_state[_df_cache_key] = add_indicators(raw_df)

df = st.session_state[_df_cache_key]

last     = df.iloc[-1]
prev     = df.iloc[-2]
close    = float(last["Close"])
signal   = get_signal(df)
strength = get_signal_strength(df)
atr_val  = float(last["ATR_14"]) if pd.notna(last.get("ATR_14")) else close * 0.02
sl_price = close - atr_val * 1.5
tp_price = close + atr_val * 1.5 * risk_reward
chg1d    = (close - float(prev["Close"])) / float(prev["Close"]) * 100
hi52     = float(df["Close"].iloc[-252:].max()) if len(df) >= 252 else float(df["Close"].max())
lo52     = float(df["Close"].iloc[-252:].min()) if len(df) >= 252 else float(df["Close"].min())
rsi_val  = float(last["RSI_14"]) if pd.notna(last.get("RSI_14")) else 50.0
macd_v   = float(last.get("MACD") or 0)
macd_sv  = float(last.get("MACD_Signal") or 0)
vol20    = float(last.get("Volatility_20") or 0)

# Build context for AI & exports
_stock_ctx = {
    "ticker": selected_ticker, "name": selected_name,
    "price": close, "change_1d": chg1d,
    "signal": signal, "strength": strength,
    "rsi": rsi_val, "macd": macd_v, "macd_signal": macd_sv,
    "sma20": float(last.get("SMA_20") or 0),
    "sma50": float(last.get("SMA_50") or 0),
    "sma200": float(last.get("SMA_200") or 0),
    "atr": atr_val, "vol": vol20,
    "hi52": hi52, "lo52": lo52,
}
st.session_state["_stock_ctx"] = _stock_ctx

def _alert_lookup(t):
    if t == selected_ticker:
        return {"price": close, "rsi": rsi_val}
    return None
_new_alerts = xp.evaluate_alerts(_alert_lookup)
if _new_alerts:
    for _a in _new_alerts:
        st.warning(f"🔔 ALERT TRIGGERED — {_a['name']}: {_a['kind'].upper()} {_a['op']} {_a['value']} "
                   f"(current: {_a.get('last_val', 0):.2f})")

# ══════════════════════════════════════════════════════════════════════════════
# KPI SUMMARY ROW
# ══════════════════════════════════════════════════════════════════════════════
k1,k2,k3,k4,k5,k6,k7 = st.columns(7)
sig_clr  = {"BUY":"#00e87a","SELL":"#ff3355","HOLD":"#ffcc00"}[signal]
chg_clr  = "#00e87a" if chg1d >= 0 else "#ff3355"
str_clr  = "#00e87a" if strength >= 65 else "#ff3355" if strength <= 35 else "#ffcc00"

currency_sym = "₹" if "Indian" in market_mode or selected_ticker.endswith(".NS") or selected_ticker.endswith(".BO") else "$"

for col, lbl, val, clr in zip(
    [k1,k2,k3,k4,k5,k6,k7],
    ["Last Close","1D Change","52W High","52W Low","RSI (14)","Signal","Strength"],
    [f"{currency_sym}{close:,.2f}",f"{'▲' if chg1d>=0 else '▼'} {abs(chg1d):.2f}%",
     f"{currency_sym}{hi52:,.2f}",f"{currency_sym}{lo52:,.2f}",f"{rsi_val:.1f}",signal,f"{strength}/100"],
    ["#ddeeff",chg_clr,"#ddeeff","#ddeeff",
     "#ff3355" if rsi_val>70 else "#00e87a" if rsi_val<30 else "#00c8ff",
     sig_clr, str_clr]
):
    col.markdown(f'<div class="glass-card"><p class="glass-label">{lbl}</p>'
                 f'<div class="glass-value" style="color:{clr};font-size:1.1rem;">{val}</div></div>',
                 unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# ══════════════════════════════════════════════════════════════════════════════
# TABS DISPATCHER
# ══════════════════════════════════════════════════════════════════════════════
TAB_OPTIONS = [
    "📊 CHART", "🔮 FORECAST", "📈 BACKTEST", "📡 SCANNER",
    "🛡️ RISK", "🛒 ORDER", "💼 PORTFOLIO", "📊 FII/DII", "🎯 OPTIONS", "📋 FUNDAMENTALS", "📰 NEWS",
    "🔥 HEATMAP", "🔄 COMPARE", "🤖 AI ANALYST", "📓 JOURNAL", "📄 EXPORT",
    "❓ MANUAL",
]

active_tab = st.radio(
    "Section",
    TAB_OPTIONS,
    horizontal=True,
    label_visibility="collapsed",
    key="xerces_active_tab",
)

def _ensure_backtest():
    if _bt_cache_key not in st.session_state:
        st.session_state[_bt_cache_key] = run_backtest(df, backtest_strategy)
    return st.session_state[_bt_cache_key]

if active_tab == "📊 CHART":
    bt_df, trades, buy_x, buy_y, sell_x, sell_y = _ensure_backtest()
    render_chart_tab(
        df=df, signal=signal, strength=strength, rsi_val=rsi_val,
        macd_v=macd_v, macd_sv=macd_sv, atr_val=atr_val, sl_price=sl_price,
        tp_price=tp_price, close=close, vol20=vol20, last=last,
        show_sma=show_sma, show_bb=show_bb, show_vol=show_vol,
        buy_x=buy_x, buy_y=buy_y, sell_x=sell_x, sell_y=sell_y, str_clr=str_clr
    )

elif active_tab == "🔮 FORECAST":
    render_forecast_tab(
        df=df, selected_name=selected_name, selected_ticker=selected_ticker,
        history_period=history_period, close=close,
        cached_forecast_bundle_func=_cached_forecast_bundle
    )

elif active_tab == "📈 BACKTEST":
    render_backtest_tab(
        df=df, selected_name=selected_name, backtest_strategy=backtest_strategy,
        ensure_backtest_func=_ensure_backtest
    )

elif active_tab == "📡 SCANNER":
    render_scanner_tab(
        SECTORS=SECTORS, allocated_capital=allocated_capital,
        risk_per_trade=risk_per_trade, risk_reward=risk_reward
    )

elif active_tab == "🛡️ RISK":
    render_risk_tab(
        df=df, selected_name=selected_name, close=close, sl_price=sl_price,
        tp_price=tp_price, allocated_capital=allocated_capital,
        risk_per_trade=risk_per_trade
    )

elif active_tab == "🛒 ORDER":
    render_order_tab(selected_name=selected_name, selected_ticker=selected_ticker, close=close)

elif active_tab == "💼 PORTFOLIO":
    render_portfolio_tab(allocated_capital=allocated_capital)

elif active_tab == "📊 FII/DII":
    render_fii_dii_tab()

elif active_tab == "🎯 OPTIONS":
    render_options_tab(selected_name=selected_name, selected_ticker=selected_ticker, close=close)

elif active_tab == "📋 FUNDAMENTALS":
    render_fundamentals_tab(selected_name=selected_name, selected_ticker=selected_ticker)

elif active_tab == "📰 NEWS":
    render_news_tab(selected_name=selected_name, selected_ticker=selected_ticker)

elif active_tab == "🔥 HEATMAP":
    render_heatmap_tab(SECTORS=SECTORS, selected_name=selected_name, selected_ticker=selected_ticker)

elif active_tab == "🔄 COMPARE":
    render_compare_tab(ALL_STOCKS=ALL_STOCKS)

elif active_tab == "🤖 AI ANALYST":
    render_ai_analyst_tab(selected_name=selected_name, selected_ticker=selected_ticker)

elif active_tab == "📓 JOURNAL":
    render_journal_tab(selected_name=selected_name, close=close, backtest_strategy=backtest_strategy)

elif active_tab == "📄 EXPORT":
    _, trades, _, _, _, _ = _ensure_backtest()
    render_export_tab(df=df, selected_name=selected_name, selected_ticker=selected_ticker, trades=trades)

elif active_tab == "❓ MANUAL":
    render_manual_tab()
