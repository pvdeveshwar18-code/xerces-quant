import streamlit as st
import plotly.graph_objects as go
import pandas as pd
from data.loader import ALL_STOCKS
from utils import credentials as cred

INDEX_META_INDIA = [
    ("^NSEI","NIFTY 50","#00e87a"), ("^NSEBANK","BANK NIFTY","#00c8ff"),
    ("^BSESN","SENSEX","#ffcc00"),  ("^CRSMID","NIFTY MIDCAP","#ff6b35"),
    ("^CNXSC","NIFTY SMALLCAP","#7c6ef8"), ("^INDIAVIX","INDIA VIX","#ff3355"),
]

INDEX_META_COMMODITIES = [
    ("GC=F","GOLD (COMEX/MCX)","#ffcc00"), ("SI=F","SILVER (COMEX/MCX)","#00c8ff"),
    ("CL=F","CRUDE OIL (WTI)","#ff6b35"),  ("BZ=F","BRENT CRUDE","#ff3355"),
    ("NG=F","NATURAL GAS","#00e87a"),       ("HG=F","COPPER","#7c6ef8"),
]

INDEX_META_US = [
    ("^GSPC","S&P 500","#00e87a"), ("^IXIC","NASDAQ","#00c8ff"),
    ("^DJI","DOW JONES","#ffcc00"), ("^RUT","RUSSELL 2000","#ff3355"),
    ("BTC-USD","BITCOIN","#7c6ef8"), ("^VIX","VOLATILITY VIX","#ff3355"),
]

def render_header(now_dt, status_text: str, status_color: str, market_mode: str = "🇮🇳 Indian Market (NSE/BSE)"):
    """Render top page header, clock, and market status."""
    col_title, col_clock, col_menu = st.columns([2, 1, 1])
    with col_title:
        st.markdown('<h1 class="xerces-title">XERCES // QUANT ENGINE</h1>', unsafe_allow_html=True)
        if "Commodities" in market_mode:
            universe_text = "COMMODITIES UNIVERSE: GOLD, SILVER, CRUDE OIL, NATGAS & METALS"
        elif "Indian" in market_mode:
            universe_text = "NSE/BSE UNIVERSE: 600+ STOCKS"
        else:
            universe_text = "US UNIVERSE: NASDAQ & NYSE TOP STOCKS"
        st.markdown(f'<p class="telemetry-tag">[ {universe_text} // ARIMA + TECHNICAL + PORTFOLIO + VIBE QUANT ENGINE // GODMODE ]</p>', unsafe_allow_html=True)
    with col_clock:
        tz_label = "IST" if ("Indian" in market_mode or "Commodities" in market_mode) else "EST"
        st.markdown(f"""
        <div style="text-align:right;font-family:'Space Mono',monospace;font-size:11px;color:#6a90aa;
                    background:rgba(7,18,32,0.5);padding:8px;border-radius:4px;border:1px solid rgba(0,200,255,0.08);">
            <div>CLOCK: <span style="color:#ffcc00;font-weight:bold;">{now_dt.strftime('%H:%M:%S')} {tz_label}</span></div>
            <div>DATE: <span style="color:#00c8ff;">{now_dt.strftime('%d %b %Y')}</span></div>
            <div style="margin-top:3px;color:{status_color};font-weight:bold;">{status_text}</div>
        </div>""", unsafe_allow_html=True)
    # Login / Logout button
    with col_menu:
        global_creds = cred.get_kotak_credentials()
        if global_creds.get("consumer_key"):
            if st.button("Logout", key="logout_btn"):
                # clear .env file
                cred.save_credentials("","","")
                st.session_state.pop("global_kotak_creds", None)
                st.experimental_rerun()
        else:
            if st.button("Login", key="login_btn"):
                with st.expander("Enter Kotak Neo Credentials"):
                    consumer_key = st.text_input("Consumer Key:", type="password")
                    mobile_number = st.text_input("Mobile Number (+91):", type="password")
                    client_code = st.text_input("Client Code:", type="password")
                    if st.button("Save Credentials"):
                        cred.save_credentials(consumer_key, mobile_number, client_code)
                        st.session_state["global_kotak_creds"] = cred.get_kotak_credentials()
                        st.success("✅ Credentials saved and will be used globally.")
                        st.experimental_rerun()
    st.markdown("<hr style='border-color:rgba(0,200,255,0.12);margin:0.65rem 0;'/>", unsafe_allow_html=True)

def render_global_search(market_mode: str = "🇮🇳 Indian Market (NSE/BSE)") -> str:
    """Render the global search bar with Market Selector. Returns search query."""
    st.markdown("<div style='background:rgba(7,18,32,0.45);border:1px solid rgba(0,200,255,0.12);padding:10px 16px;border-radius:6px;margin-bottom:12px;'>", unsafe_allow_html=True)
    sc1, sc2 = st.columns([5, 1])
    if "Commodities" in market_mode:
        placeholder_txt = "Search Commodity — GOLD, SILVER, CRUDEOIL, NATURALGAS, COPPER..."
    elif "Indian" in market_mode:
        placeholder_txt = "Search Indian stock — Reliance, TCS, SBIN, INFY..."
    else:
        placeholder_txt = "Search US stock — NVDA, AAPL, MSFT, TSLA, SPY..."
    with sc1:
        search_raw = st.text_input("Search", value="", placeholder=placeholder_txt, label_visibility="collapsed")
    with sc2:
        if search_raw and st.button("✕ Clear", use_container_width=True):
            st.session_state["search_val"] = ""
            st.rerun()
    st.markdown("</div>", unsafe_allow_html=True)
    return search_raw.strip()

def render_dashboard_landing(idx_data: dict[str, pd.DataFrame], market_mode: str = "🇮🇳 Indian Market (NSE/BSE)"):
    """Render market dashboard landing page when no stock is searched."""
    if "Commodities" in market_mode:
        m_label = "COMMODITIES (MCX / GLOBAL)"
        INDEX_META = INDEX_META_COMMODITIES
        currency_sym = "$"
    elif "Indian" in market_mode:
        m_label = "INDIAN NSE/BSE"
        INDEX_META = INDEX_META_INDIA
        currency_sym = "₹"
    else:
        m_label = "US NASDAQ/NYSE"
        INDEX_META = INDEX_META_US
        currency_sym = "$"

    st.markdown(f'<h2 class="xerces-title" style="font-size:1.5rem;margin-bottom:12px;">📊 LIVE {m_label} MARKET OVERVIEW</h2>', unsafe_allow_html=True)

    cols = st.columns(6)
    for col, (sym, name, clr) in zip(cols, INDEX_META):
        try:
            idf  = idx_data.get(sym)
            if idf is None or len(idf) < 2:
                col.warning(name); continue
            cv   = float(idf["Close"].iloc[-1])
            pv   = float(idf["Close"].iloc[-2])
            chg  = (cv - pv) / pv * 100
            flip = "VIX" in sym
            cclr = ("#ff3355" if chg >= 0 else "#00e87a") if flip else ("#00e87a" if chg >= 0 else "#ff3355")
            arrow= "▲" if chg >= 0 else "▼"
            col.markdown(f"""
            <div class="glass-card">
                <p class="glass-label" style="color:{clr};">{name}</p>
                <div class="glass-value" style="font-size:1.1rem;">{currency_sym}{cv:,.2f}</div>
                <p style="font-size:11px;color:{cclr};margin:2px 0;font-weight:600;">{arrow} {abs(chg):.2f}%</p>
            </div>
            """, unsafe_allow_html=True)
        except Exception:
            col.warning(name)

    try:
        main_sym = "^NSEI" if "Indian" in market_mode else "^GSPC"
        main_title = "Nifty 50 Index" if "Indian" in market_mode else "S&P 500 Index"
        main_df = idx_data.get(main_sym)
        if main_df is not None and not main_df.empty:
            fig0 = go.Figure()
            fig0.add_trace(go.Scatter(x=main_df["Date"], y=main_df["Close"], line=dict(color="#00e87a",width=2), name=main_title, fill="tozeroy", fillcolor="rgba(0,232,122,0.04)"))
            fig0.update_layout(height=280, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#ddeeff",family="Space Mono",size=10), margin=dict(l=10,r=10,t=10,b=10),
                xaxis=dict(gridcolor="rgba(0,200,255,0.05)"), yaxis=dict(gridcolor="rgba(0,200,255,0.05)",tickprefix=currency_sym),
                showlegend=False)
            st.plotly_chart(fig0, use_container_width=True)
    except Exception:
        pass

    example_stocks = "<b style='color:#00c8ff;'>Reliance</b>, <b style='color:#00c8ff;'>TCS</b>, <b style='color:#00c8ff;'>HDFCBANK</b>" if "Indian" in market_mode else "<b style='color:#00c8ff;'>NVDA</b>, <b style='color:#00c8ff;'>AAPL</b>, <b style='color:#00c8ff;'>TSLA</b>"
    st.markdown(f"""
    <div class="glass-card" style="margin-top:10px;">
        <p class="section-header" style="margin-top:0;">💡 How to use XERCES</p>
        <p style="font-size:12px;color:#a0aec0;line-height:1.7;margin:0;">
        Type any stock name or symbol in the search bar above — e.g. {example_stocks}.
        You'll get live technical charts with MACD/RSI/Bollinger Bands, ARIMA + Holt-Winters price forecast,
        multi-strategy backtesting, bulk market scanner, portfolio optimizer (MPT), news sentiment, Vibe Strategy AI Copilot, and full risk calculator.
        </p>
    </div>
    """, unsafe_allow_html=True)
