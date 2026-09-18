# XERCES Quant Engine

XERCES is a Streamlit dashboard for equity research, technical analysis, forecasting, backtesting, portfolio review, alerts, broker simulation, AI-assisted analysis, and report export.

The app is focused primarily on Indian NSE/BSE equities, with partial support for US market symbols and indices.

## Features

- Market dashboard with major index snapshots.
- Stock search with NSE/BSE ticker resolution and symbol aliases.
- Candlestick charts with SMA, Bollinger Bands, RSI, MACD, stochastic, volume, ATR, and ML signal scoring.
- Forecasting with ARIMA, Holt-Winters, naive baseline, validation metrics, and weighted ensemble targets.
- Backtesting for SMA crossover, RSI mean reversion, Bollinger breakout, and MACD crossover strategies.
- Bulk sector scanner with BUY/SELL/HOLD signals and position sizing.
- Risk calculator with position sizing, VaR/CVaR, and historical stress scenarios.
- Portfolio tracker, rotation advisor, Monte Carlo allocation optimizer, and exit strategy planner.
- FII/DII, options chain, fundamentals, news sentiment, heatmap, comparison, journal, broker, AI analyst, and export tabs.
- PDF and Excel report generation.

## Requirements

Install dependencies from `requirements.txt`:

```bash
pip install -r requirements.txt
```

Optional AI features require one or both of these secrets:

```text
GEMINI_API_KEY = "your-google-gemini-key"
EMERGENT_LLM_KEY = "your-emergent-key"
```

## Run Locally

```bash
streamlit run app.py
```

Streamlit opens the app at:

```text
http://localhost:8501
```

## Data Storage

XERCES writes local app state such as watchlists, alerts, journals, chat history, and SQLite data under the project `data` directory by default.

To override that location, set:

```bash
XERCES_DATA_DIR=/path/to/xerces-data
```

## Streamlit Cloud

1. Push the project files to your repository.
2. Deploy `app.py` on Streamlit Community Cloud.
3. Add API keys in Streamlit secrets if you want AI analysis.
4. Confirm the app can write to its configured data directory.

## Disclaimer

XERCES is a research and analysis tool. It is not SEBI registered and does not provide financial advice. Market data and generated analysis can be delayed, incomplete, or wrong. Always verify independently before making trading or investment decisions.
