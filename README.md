# XERCES // Quant Engine

A next-generation Streamlit dashboard for Indian equity (NSE/BSE) analysis — 600+ stocks across 18 sectors, complete with technical indicators, AI analyst, forecasting, backtesting, and portfolio optimization.

## Features

### 📊 Core Analytics (11 tabs)
- **Chart** — Candlesticks, SMA 20/50/200, Bollinger Bands, RSI, MACD, Stochastic, Volume
- **Forecast** — ARIMA (5×5 AIC grid search) + Holt-Winters consensus with 60-day MAPE + directional accuracy
- **Backtest** — 4 strategies (SMA/RSI/BB/MACD) on 5-year data, next-day open execution
- **Scanner** — Bulk multi-sector scanner with BUY/SELL/HOLD signals + position sizing
- **Risk Calculator** — Position-sizing based on ATR and R:R
- **Portfolio** — MPT optimizer (3000 Monte Carlo simulations) + custom portfolio tracker with rotation advisor
- **FII/DII Flows** — Live NSE institutional flow data
- **Options Chain** — Full option chain, PCR, Max Pain analysis
- **Fundamentals** — P/E, P/B, ROE, ROCE, Debt/Equity, EPS from Screener.in
- **News & Sentiment** — Google News / Yahoo RSS with keyword-based sentiment scoring
- **Manual** — Complete reference guide

### 🚀 XERCES+ Enhancements (5 new tabs)
- **🔥 Heatmap** — Live 1-day sector performance + 5-min intraday candles
- **🔄 Compare** — Side-by-side 2–4 stocks with correlation matrix + risk/return stats
- **🤖 AI Analyst** — Multi-turn chatbot powered by Claude Sonnet 4.6 / GPT-5.4 / Gemini. One-click trade thesis & news summarization
- **📓 Journal** — Persistent trade log with P&L tracking, win-rate, equity curve
- **📄 Export** — PDF stock reports (with optional AI thesis) + multi-sheet Excel workbook

### ⭐ Sidebar
- **Watchlist** — Persistent, add/remove any stock
- **Alerts** — Price / RSI threshold alerts, auto-triggered on refresh

---

## Run Locally

```bash
git clone https://github.com/pvdeveshwar18-code/arima.git
cd arima
pip install -r requirements.txt
streamlit run app.py
```

Opens at `http://localhost:8501`.

---

## Deploy to Streamlit Community Cloud (free public URL)

1. **Push these files to your repo:**
   - `app.py` (the new enhanced version)
   - `xerces_plus.py` (new — enhancement module)
   - `requirements.txt` (updated)
   - `.streamlit/config.toml` (optional theme file)
   - `readme.md`

2. **Add a secret for AI features:**
   - Go to [share.streamlit.io](https://share.streamlit.io) → deploy your app
   - In the app settings, add a secret:
     ```toml
     EMERGENT_LLM_KEY = "sk-emergent-2191f894997De47509"
     ```
   - Or use your own OpenAI / Anthropic / Google key — see below.

3. **Done.** You'll get a permanent URL like `https://xerces.streamlit.app`.

---

## Using Your Own LLM Key (optional)

XERCES ships with the Emergent LLM Key, which works across Claude, GPT, and Gemini. If you want to bypass it, open `xerces_plus.py` and swap this line:

```python
EMERGENT_LLM_KEY = os.environ.get("EMERGENT_LLM_KEY", "sk-emergent-2191f894997De47509")
```

Replace with your own key (OpenAI / Anthropic / Google) and update the provider in `_ai_chat_async` accordingly.

---

## Persistence

XERCES stores watchlist / alerts / journal in the `data/` folder as JSON/CSV — created automatically on first use.

---

## Disclaimer

XERCES is a research and analysis tool. Not SEBI registered. Not financial advice. Data from Yahoo Finance / NSE / Screener.in. Always do your own due diligence.
