"""
XERCES Deep Analytics & Forecasting Tab Module
Includes Plotly/TradingView charts, Ensemble Forecasting with GARCH volatility, Backtesting, Fundamentals, and News Sentiment.
"""

import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from ui.components.tradingview_chart import render_tradingview_chart
from forecasting.forecast_engine import MultiModelForecastEngine
from data.market_data import fetch_news, fetch_fundamentals

def render_analytics_tab(
    df,
    ticker: str,
    selected_name: str,
    show_tv_chart: bool = False,
    show_bb: bool = True,
    show_sma: bool = True,
    show_vol: bool = True,
    bt_data: tuple = None
):
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📊 TECHNICAL CHART", "🔮 ENSEMBLE FORECAST", "📈 STRATEGY BACKTEST", "📋 FUNDAMENTALS", "📰 NEWS & SENTIMENT"
    ])

    with tab1:
        st.subheader(f"📊 Technical Analysis — {selected_name} ({ticker})")
        if show_tv_chart:
            st.caption("HTML5 TradingView Lightweight Intraday Chart Widget")
            render_tradingview_chart(ticker, height=620)
        else:
            rows = 4 if show_vol else 3
            row_h = ([0.48, 0.18, 0.18, 0.16] if show_vol else [0.56, 0.22, 0.22])
            titles = ["Price + Indicators", "RSI (14)", "MACD"] + (["Volume"] if show_vol else [])
            fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, row_heights=row_h, vertical_spacing=0.025, subplot_titles=titles)
            fig.add_trace(go.Candlestick(x=df["Date"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"], name="OHLC"), row=1, col=1)

            if show_sma:
                for col_n, clr, dsh in [("SMA_20", "#00c8ff", "dot"), ("SMA_50", "#ffcc00", "dash"), ("SMA_200", "#ff6b35", "solid")]:
                    if col_n in df.columns:
                        fig.add_trace(go.Scatter(x=df["Date"], y=df[col_n], name=col_n.replace("_", " "), line=dict(color=clr, width=1.2, dash=dsh)), row=1, col=1)

            if show_bb and "BB_Upper" in df.columns:
                fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_Upper"], name="BB Upper", line=dict(color="rgba(0, 200, 255, 0.4)", dash="dash")), row=1, col=1)
                fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_Lower"], name="BB Lower", line=dict(color="rgba(0, 200, 255, 0.4)", dash="dash"), fill="tonexty"), row=1, col=1)

            if "RSI_14" in df.columns:
                fig.add_trace(go.Scatter(x=df["Date"], y=df["RSI_14"], name="RSI", line=dict(color="#00e87a", width=1.5)), row=2, col=1)
                fig.add_hline(y=70, line_dash="dash", line_color="#ff3355", row=2, col=1)
                fig.add_hline(y=30, line_dash="dash", line_color="#00e87a", row=2, col=1)

            if "MACD" in df.columns:
                fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD"], name="MACD", line=dict(color="#00c8ff", width=1.5)), row=3, col=1)
                fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD_Signal"], name="Signal", line=dict(color="#ffcc00", width=1.5)), row=3, col=1)

            if show_vol and "Volume" in df.columns:
                fig.add_trace(go.Bar(x=df["Date"], y=df["Volume"], name="Volume", marker_color="rgba(0, 200, 255, 0.3)"), row=4, col=1)

            fig.update_layout(template="plotly_dark", height=650, xaxis_rangeslider_visible=False)
            st.plotly_chart(fig, use_container_width=True)

    with tab2:
        st.subheader("🔮 Consensus Multi-Model Price Forecast (GARCH + ARIMA + ETS)")
        fc_days = st.slider("Forecast Horizon (Days)", min_value=10, max_value=120, value=30, step=10)

        with st.spinner(f"Computing multi-model forecast with GARCH(1,1) volatility bounds for {fc_days} days..."):
            ens_res = MultiModelForecastEngine.forecast_consensus(df, forecast_days=fc_days)

        if ens_res.get("error"):
            st.error(ens_res["error"])
        else:
            e1, e2, e3, e4 = st.columns(4)
            e1.metric("Target Price", f"₹{ens_res['forecast_target']:,.2f}", f"{ens_res['forecast_pct_change']:+.2f}%")
            e2.metric("Directional Bias", ens_res['directional_bias'])
            e3.metric("GARCH Annualized Vol", f"{ens_res['garch_annualized_vol']}%")
            e4.metric("95% Upper Limit", f"₹{ens_res['upper_95']:,.2f}")

            fc_df = ens_res["forecast_df"]
            fig_fc = go.Figure()
            fig_fc.add_trace(go.Scatter(x=fc_df.index, y=fc_df['Consensus_Forecast'], name="Consensus Forecast", line=dict(color="#00c8ff", width=2.5)))
            fig_fc.add_trace(go.Scatter(x=fc_df.index, y=fc_df['ARIMA_Forecast'], name="ARIMA Forecast", line=dict(color="#ffcc00", dash="dot")))
            fig_fc.add_trace(go.Scatter(x=fc_df.index, y=fc_df['ETS_Forecast'], name="Holt-Winters ETS", line=dict(color="#7c6ef8", dash="dot")))
            fig_fc.add_trace(go.Scatter(x=fc_df.index, y=fc_df['Upper_95'], name="Upper 95% (GARCH)", line=dict(color="rgba(0, 200, 255, 0.3)", dash="dash")))
            fig_fc.add_trace(go.Scatter(x=fc_df.index, y=fc_df['Lower_95'], name="Lower 95% (GARCH)", line=dict(color="rgba(0, 200, 255, 0.3)", dash="dash"), fill="tonexty"))

            fig_fc.update_layout(template="plotly_dark", height=480, yaxis=dict(tickprefix="₹"))
            st.plotly_chart(fig_fc, use_container_width=True)

    with tab3:
        st.subheader("📈 Backtesting Engine")
        if bt_data:
            bt_df, trades, buy_x, buy_y, sell_x, sell_y = bt_data
            wins = sum(1 for t in trades if t["Result"] == "✅ WIN")
            win_rate = (wins / len(trades) * 100.0) if trades else 0.0

            b1, b2, b3 = st.columns(3)
            b1.metric("Strategy Cumulative Return", f"{bt_df['Close'].pct_change().sum()*100:.2f}%")
            b2.metric("Total Trades Executed", len(trades))
            b3.metric("Win Rate", f"{win_rate:.1f}%")

            if trades:
                st.markdown("### 📋 Trade Log")
                st.dataframe(trades, use_container_width=True)

    with tab4:
        st.subheader(f"📋 Fundamentals — {selected_name} (Screener.in Data)")
        with st.spinner("Fetching fundamentals..."):
            funds, url = fetch_fundamentals(ticker)

        if funds:
            f_cols = st.columns(4)
            for idx, (k, v) in enumerate(funds.items()):
                val_str = f"{v:,.2f}" if isinstance(v, (int, float)) else "N/A"
                f_cols[idx % 4].markdown(f'<div class="glass-card"><p class="glass-label">{k}</p><div class="glass-value" style="color:#00c8ff;">{val_str}</div></div>', unsafe_allow_html=True)
            st.caption(f"Source: [Screener.in]({url})")
        else:
            st.info("Fundamental ratios unavailable for this ticker.")

    with tab5:
        st.subheader(f"📰 News & Sentiment Scoring — {selected_name}")
        with st.spinner("Fetching news feed..."):
            news_items = fetch_news(ticker, selected_name)

        if news_items:
            for item in news_items[:10]:
                st.markdown(f"- [{item['title']}]({item['link']}) — *{item['date']}*")
        else:
            st.info("No recent news stories found for this company.")
