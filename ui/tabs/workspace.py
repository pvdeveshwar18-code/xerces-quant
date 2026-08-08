"""
XERCES Trader Workspace & Exports Tab Module
Includes AI Analyst Chatbot, Trade Journal, PDF/Excel Exports, and Godmode Reference Manual.
"""

import streamlit as st
import xerces_plus as xp

def render_workspace_tab(ticker: str, selected_name: str, stock_ctx: dict, df):
    tab1, tab2, tab3, tab4 = st.tabs([
        "🤖 AI ANALYST CHAT", "📓 TRADE JOURNAL", "📄 EXPORT PDF/EXCEL", "❓ REFERENCE MANUAL"
    ])

    with tab1:
        xp.render_ai_tab(ticker, selected_name, stock_ctx)

    with tab2:
        xp.render_journal_tab()

    with tab3:
        xp.render_export_tab(ticker, selected_name, stock_ctx, df)

    with tab4:
        st.markdown('''
<div class="glass-card">
<p class="section-header" style="margin-top:0;">[ XERCES GODMODE — REFERENCE MANUAL ]</p>
<div style="font-size:11px;color:#8ab0cc;line-height:2.1;font-family:'Space Mono',monospace;">
<b style="color:#00c8ff;">RSI (14)</b> — &lt;30 oversold (buy zone). &gt;70 overbought (sell zone).<br>
<b style="color:#00c8ff;">MACD (12,26,9)</b> — MACD crossing above signal = bullish momentum. Histogram shows acceleration.<br>
<b style="color:#00c8ff;">SMA 20/50/200</b> — Golden cross (SMA50 &gt; SMA200) = major bull signal. Price &gt; SMA200 = bull market.<br>
<b style="color:#00c8ff;">Bollinger Bands</b> — Band squeeze = volatility expansion imminent. Breakout direction = trend.<br>
<b style="color:#00c8ff;">ATR (14)</b> — True range in Rs. Used for stop-loss sizing: 1.5x ATR below entry.<br>
<b style="color:#ffcc00;">GARCH + ARIMA ENSEMBLE</b> — Heteroskedastic volatility modeling combined with log ARIMA returns and Holt-Winters.<br>
<b style="color:#7c4dff;">MONTE CARLO STRESS TEST</b> — Simulates 5,000–10,000 paths for VaR/CVaR Expected Shortfall under 2008 & COVID crash shocks.<br>
<b style="color:#00e87a;">🤖 ML SIGNAL CLASSIFIER</b> — Scikit-learn Random Forest & XGBoost multi-factor BUY/SELL probability scoring.<br>
<b style="color:#00e87a;">🏛️ MACRO TABLEAU OVERVIEW</b> — Embedded interactive macro dashboard (Indian stock market.html).<br>
<b style="color:#ff3355;">DISCLAIMER:</b> XERCES is a research tool. Not SEBI registered. Not financial advice. Data from Yahoo Finance.
</div>
</div>
''', unsafe_allow_html=True)
