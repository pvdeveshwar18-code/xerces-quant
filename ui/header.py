"""
XERCES UI Header Component
Renders the main title banner, market clock, IST time, and NSE market status indicator.
"""

import datetime
import pytz
import streamlit as st

IST = pytz.timezone("Asia/Kolkata")

def ist_now():
    return datetime.datetime.now(IST)

def market_status():
    now = ist_now()
    if now.weekday() >= 5:
        return "🔴 NSE CLOSED", "#ff3355"
    ot = now.replace(hour=9, minute=15, second=0, microsecond=0)
    ct = now.replace(hour=15, minute=30, second=0, microsecond=0)
    if ot <= now <= ct:
        return "🟢 NSE OPEN", "#00e87a"
    return "🔴 NSE CLOSED", "#ff3355"

def render_header():
    col_title, col_clock = st.columns([2, 1])
    with col_title:
        st.markdown('<h1 class="xerces-title">XERCES // QUANT ENGINE</h1>', unsafe_allow_html=True)
        st.markdown('<p class="telemetry-tag">[ NSE/BSE UNIVERSE: 600+ STOCKS // ARIMA + GARCH + ML CLASSIFIER // GODMODE ]</p>', unsafe_allow_html=True)
    with col_clock:
        now_ist = ist_now()
        ms, mc = market_status()
        st.markdown(f"""
        <div style="text-align:right;font-family:'Space Mono',monospace;font-size:11px;color:#6a90aa;
                    background:rgba(7,18,32,0.5);padding:8px;border-radius:4px;border:1px solid rgba(0,200,255,0.08);">
            <div>CLOCK: <span style="color:#ffcc00;font-weight:bold;">{now_ist.strftime('%H:%M:%S')} IST</span></div>
            <div>DATE: <span style="color:#00c8ff;">{now_ist.strftime('%d %b %Y')}</span></div>
            <div style="margin-top:3px;color:{mc};font-weight:bold;">{ms}</div>
        </div>""", unsafe_allow_html=True)

    st.markdown("<hr style='border-color:rgba(0,200,255,0.12);margin:0.65rem 0;'>", unsafe_allow_html=True)
