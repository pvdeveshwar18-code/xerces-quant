import streamlit as st

def render_manual_tab():
    """Render Manual & Reference Guide tab."""
    st.markdown('<p class="section-header">[ ❓ MANUAL & REFERENCE GUIDE ]</p>', unsafe_allow_html=True)
    st.markdown("""
### ⚡ XERCES // QUANT ENGINE — Complete User Reference

#### 1. Core Analytics
- **Chart**: Multi-panel candlestick chart with SMA 20/50/200, Bollinger Bands, RSI (14), MACD, and Volume.
- **Forecast**: Ensembled ARIMA + Holt-Winters + Naive forecasting model validated against 60-day holdout windows.
- **Backtest**: Walk-forward backtesting with next-day open execution across 4 technical strategies.
- **Scanner**: Multi-stock, multi-sector technical scanner with position sizing and buy/sell signals.
- **Risk Calculator**: Dynamic position sizing calculator based on ATR, account equity, and R:R ratios.
- **Portfolio**: Monte Carlo 3000 Efficient Frontier optimizer & custom portfolio rotation advisor.

#### 2. Institutional & Fundamental Data
- **FII/DII**: Daily institutional net buy/sell flow data directly from NSE India.
- **Options Chain**: Strike-level Open Interest (OI), Put/Call Ratio (PCR), and Max Pain analysis.
- **Fundamentals**: Key valuation metrics and ratios scraped live from Screener.in.
- **News**: RSS headlines aggregated from Google News with financial keyword sentiment analysis.

#### 3. XERCES+ Modules
- **Heatmap**: Sector performance matrix and 5-min intraday candle tracking.
- **Compare**: Multi-stock side-by-side relative performance and correlation matrix.
- **AI Analyst**: LLM-powered market analysis, news summarization, and trade thesis generation.
- **Journal**: Persistent local trade log with equity curve and win-rate analytics.
- **Export**: Professional PDF research report generator and multi-sheet Excel exporter.
""")
