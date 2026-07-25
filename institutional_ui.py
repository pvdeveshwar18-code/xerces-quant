"""
XERCES Institutional UI Extension
Renders top-tier Institutional Engine UI components: Decision Engine, Risk & Kelly, Black-Litterman, AI Committee, and Trade Planner.
"""

import streamlit as st
import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px

from analytics.market_regime import MarketRegimeDetector
from analytics.relative_strength import RelativeStrengthEngine
from decision.decision_engine import InstitutionalDecisionEngine
from risk.risk_engine import InstitutionalRiskEngine
from portfolio.black_litterman import BlackLittermanEngine
from forecasting.ensemble import EnsembleForecastingEngine
from trade_planner.trade_planner import InstitutionalTradePlanner
from ai_committee.ai_committee import AIInvestmentCommittee
from journal.journal_ai import JournalIntelligenceEngine
from backtesting.strategy_lab import StrategyLabEngine

def render_decision_engine_tab(df: pd.DataFrame, ticker: str, fundamentals: dict = None):
    """
    Renders Decision Engine tab content.
    """
    st.subheader("🎯 Institutional Decision Engine")
    st.caption("Synthesizes Market Regime, Relative Strength, Risk Parameters, Technical Momentum, and Fundamentals into a unified Decision Matrix.")

    if df is None or len(df) < 50:
        st.warning("Insufficient data available for Decision Engine evaluation (minimum 50 bars required).")
        return

    dec_res = InstitutionalDecisionEngine.evaluate_stock(df, ticker=ticker, fundamentals=fundamentals)

    signal = dec_res['signal']
    score = dec_res['score']
    confidence = dec_res['confidence_pct']

    col1, col2, col3, col4 = st.columns(4)
    with col1:
        st.markdown(f"**Institutional Signal**\n### `{signal}`")
    with col2:
        st.markdown(f"**Decision Score**\n### `{score} / 100`")
    with col3:
        st.markdown(f"**Confidence Level**\n### `{confidence}%`")
    with col4:
        st.markdown(f"**Risk:Reward Ratio**\n### `{dec_res['risk_reward_ratio']} : 1`")

    st.markdown("---")
    
    # Trade Levels
    l_col1, l_col2, l_col3, l_col4 = st.columns(4)
    l_col1.metric("Current Entry Price", f"₹{dec_res['entry_price']:,.2f}")
    l_col2.metric("ATR Stop Loss", f"₹{dec_res['stop_loss']:,.2f}", f"-₹{dec_res['risk_per_share']:,.2f}")
    l_col3.metric("Target 1 (1:2 R:R)", f"₹{dec_res['target_1']:,.2f}")
    l_col4.metric("Target 2 (1:3.2 R:R)", f"₹{dec_res['target_2']:,.2f}")

    st.markdown("#### 💡 Trade Thesis & Key Drivers")
    st.info(dec_res['thesis'])

    # Detailed Factor Breakdown
    st.markdown("#### 🔍 Factor Breakdown Matrix")
    reg_info = dec_res['regime_info']
    rs_info = dec_res['rs_info']
    risk_info = dec_res['risk_info']

    fb_col1, fb_col2 = st.columns(2)
    with fb_col1:
        st.markdown(f"""
        - **Market Regime**: `{reg_info.get('regime')}`
        - **Trend Strength (ADX)**: `{reg_info.get('trend_strength_adx')} ({reg_info.get('adx_signal')})`
        - **Volatility Regime**: `{reg_info.get('volatility_regime')}` (ATR: `{reg_info.get('atr_percent')}%`)
        - **Moving Average Alignment**: `{reg_info.get('ema_alignment')}`
        """)
    with fb_col2:
        st.markdown(f"""
        - **Mansfield Relative Strength**: `{rs_info.get('mrs'):+.2f}%` vs `{rs_info.get('benchmark')}`
        - **RS Status**: `{rs_info.get('rs_status')}` (`{rs_info.get('rs_trend')}`)
        - **Outperformance vs Index**: `{rs_info.get('outperformance_pct'):+.2f}%`
        - **Annualized Volatility**: `{risk_info.get('annualized_volatility')}%`
        """)

def render_risk_and_kelly_tab(df: pd.DataFrame, ticker: str):
    """
    Renders Risk Engine & Kelly Criterion tab content.
    """
    st.subheader("🛡️ Institutional Risk & Kelly Sizing Engine")
    st.caption("Calculates Value-at-Risk (VaR 95%/99%), Conditional VaR (Expected Shortfall), Maximum Drawdown, and Kelly Criterion optimal leverage.")

    if df is None or len(df) < 30:
        st.warning("Insufficient data available for Risk Engine.")
        return

    account_capital = st.number_input("Account Portfolio Capital (₹)", value=500000, step=50000, key="risk_cap_input")

    risk_res = InstitutionalRiskEngine.calculate_risk_metrics(df, portfolio_value=account_capital)

    rc1, rc2, rc3, rc4 = st.columns(4)
    rc1.metric("1-Day Parametric VaR (95%)", f"₹{risk_res['var_95_amount']:,.2f}", f"-{risk_res['var_95_pct']}%")
    rc2.metric("Expected Shortfall (CVaR 95%)", f"₹{risk_res['cvar_95_amount']:,.2f}", f"-{risk_res['cvar_95_pct']}%")
    rc3.metric("Max Drawdown (Historical)", f"-{risk_res['max_drawdown_pct']}%")
    rc4.metric("Optimal Half-Kelly Allocation", f"{risk_res['kelly_pct']}%", f"Win Rate: {risk_res['win_rate_pct']}%")

    st.markdown("---")

    rk_col1, rk_col2 = st.columns(2)
    with rk_col1:
        st.markdown("#### 📊 Risk-Adjusted Ratios")
        st.write(f"- **Sharpe Ratio (Annualized)**: `{risk_res['sharpe_ratio']}`")
        st.write(f"- **Sortino Ratio (Downside Risk)**: `{risk_res['sortino_ratio']}`")
        st.write(f"- **Annualized Volatility**: `{risk_res['annualized_volatility']}%`")
        st.write(f"- **Historical Win/Loss Payoff Ratio**: `{risk_res['win_loss_ratio']}:1`")
    with rk_col2:
        st.markdown("#### 💡 Kelly Allocation Guidance")
        st.info(
            f"Based on historical return distribution, the **Half-Kelly** rule recommends allocating a maximum of **{risk_res['kelly_pct']}%** "
            f"(₹{account_capital * (risk_res['kelly_fraction']):,.2f}) of your account capital to `{ticker}` to maximize long-term logarithmic capital growth while mitigating ruin risk."
        )

def render_black_litterman_tab():
    """
    Renders Black-Litterman Portfolio Optimization tab content.
    """
    st.subheader("🏛️ Black-Litterman Institutional Portfolio Optimization")
    st.caption("Combines Implied Market Equilibrium Returns with custom Absolute/Relative Investor Views to construct optimal asset weights.")

    st.markdown("#### 📈 Enter Portfolio Tickers & Custom Views")
    tickers_input = st.text_input("Enter NSE Stock Tickers (comma separated)", "RELIANCE.NS, TCS.NS, INFY.NS, HDFCBANK.NS, ICICIBANK.NS")

    ticker_list = [t.strip().upper() for t in tickers_input.split(",") if t.strip()]

    if len(ticker_list) < 2:
        st.warning("Please enter at least 2 tickers for portfolio optimization.")
        return

    st.markdown("##### Custom Investor Views (Optional)")
    view_asset = st.selectbox("Select Asset for View", ticker_list, index=0)
    view_return_pct = st.slider("Expected Annual Return View (%)", min_value=-30.0, max_value=50.0, value=15.0, step=1.0)
    view_conf = st.slider("View Confidence Level (%)", min_value=10, max_value=100, value=75, step=5)

    if st.button("🚀 Run Black-Litterman Optimization", use_container_width=True):
        with st.spinner("Downloading historical price series and solving Black-Litterman quadratic program..."):
            try:
                import yfinance as yf
                data = yf.download(ticker_list, period="2y", progress=False)['Close']
                returns_df = data.pct_change().dropna()

                custom_views = [{
                    'type': 'absolute',
                    'asset': view_asset,
                    'return': view_return_pct / 100.0,
                    'confidence': view_conf / 100.0
                }]

                bl_res = BlackLittermanEngine.optimize_portfolio(returns_df, views=custom_views)

                bl_col1, bl_col2, bl_col3 = st.columns(3)
                bl_col1.metric("Expected Portfolio Return", f"{bl_res['portfolio_expected_return_pct']}%")
                bl_col2.metric("Portfolio Volatility", f"{bl_res['portfolio_volatility_pct']}%")
                bl_col3.metric("Black-Litterman Sharpe Ratio", f"{bl_res['portfolio_sharpe_ratio']}")

                st.markdown("---")
                st.markdown("#### ⚖️ Optimal Asset Weight Allocation")
                
                weights_df = pd.DataFrame({
                    "Ticker": list(bl_res['weights_pct'].keys()),
                    "Prior Equilibrium Return (%)": list(bl_res['prior_equilibrium_returns_pct'].values()),
                    "Black-Litterman Posterior Return (%)": list(bl_res['bl_posterior_returns_pct'].values()),
                    "Optimal Weight (%)": list(bl_res['weights_pct'].values())
                })

                st.dataframe(weights_df, use_container_width=True)

                # Pie Chart
                fig = px.pie(weights_df, values="Optimal Weight (%)", names="Ticker", title="Black-Litterman Optimal Weight Allocation", hole=0.4)
                fig.update_layout(template="plotly_dark")
                st.plotly_chart(fig, use_container_width=True)

            except Exception as e:
                st.error(f"Error executing Black-Litterman optimization: {str(e)}")

def render_ai_committee_tab(ticker: str, df: pd.DataFrame, fundamentals: dict = None):
    """
    Renders AI Investment Committee tab content.
    """
    st.subheader("🤖 AI Investment Committee Vote")
    st.caption("Multi-agent committee simulation (Technicals, Fundamentals, Macro/Regime, Risk, Sentiment).")

    if df is None or len(df) < 30:
        st.warning("Insufficient data available for AI Committee evaluation.")
        return

    dec_res = InstitutionalDecisionEngine.evaluate_stock(df, ticker=ticker, fundamentals=fundamentals)
    comm_res = AIInvestmentCommittee.evaluate_committee(ticker, df, dec_res, fundamentals=fundamentals)

    vote = comm_res['consensus_vote']
    score = comm_res['consensus_score']

    v_col1, v_col2 = st.columns(2)
    v_col1.markdown(f"**Committee Consensus Vote**\n### `{vote}`")
    v_col2.markdown(f"**Consensus Rating Score**\n### `{score} / 100`")

    st.markdown("---")
    st.markdown("#### 👥 Member Individual Votes & Statements")

    for member, details in comm_res['committee_members'].items():
        with st.expander(f"{member} — Vote: {details['vote']} (Score: {details['score']}/100)", expanded=True):
            st.markdown(f"**Rationale**: {details['comment']}")

def render_trade_planner_tab(df: pd.DataFrame, ticker: str):
    """
    Renders Trade Planner tab content.
    """
    st.subheader("📊 Institutional Trade Planner")
    st.caption("Computes exact position size, quantity of shares, and cash required based on fixed risk parameters.")

    if df is None or len(df) < 10:
        st.warning("No price data available.")
        return

    latest_price = float(df['Close'].iloc[-1])
    atr = (df['High'] - df['Low']).rolling(14).mean().iloc[-1] if 'High' in df.columns else latest_price * 0.02
    def_sl = round(latest_price - (2.0 * atr), 2)
    def_t1 = round(latest_price + (2.0 * (latest_price - def_sl)), 2)
    def_t2 = round(latest_price + (3.2 * (latest_price - def_sl)), 2)

    tp_col1, tp_col2 = st.columns(2)
    with tp_col1:
        total_cap = st.number_input("Total Account Capital (₹)", value=500000, step=25000, key="tp_cap")
        risk_pct = st.slider("Max Account Risk per Trade (%)", min_value=0.25, max_value=5.0, value=1.0, step=0.25, key="tp_risk")
        max_pos_pct = st.slider("Max Portfolio Position Size Limit (%)", min_value=5.0, max_value=50.0, value=20.0, step=5.0, key="tp_max_pos")

    with tp_col2:
        entry_p = st.number_input("Entry Price (₹)", value=float(latest_price), step=1.0, key="tp_entry")
        sl_p = st.number_input("Stop Loss Price (₹)", value=float(def_sl), step=1.0, key="tp_sl")
        t1_p = st.number_input("Target 1 Price (₹)", value=float(def_t1), step=1.0, key="tp_t1")
        t2_p = st.number_input("Target 2 Price (₹)", value=float(def_t2), step=1.0, key="tp_t2")

    plan = InstitutionalTradePlanner.calculate_trade_plan(
        total_capital=total_cap,
        risk_per_trade_pct=risk_pct,
        entry_price=entry_p,
        stop_loss=sl_p,
        target_1=t1_p,
        target_2=t2_p,
        max_position_pct=max_pos_pct
    )

    if "error" in plan:
        st.error(plan["error"])
        return

    st.markdown("---")
    st.markdown("#### 📋 Execution Orders Summary")

    p1, p2, p3, p4 = st.columns(4)
    p1.metric("Shares to Buy", f"{plan['shares_to_buy']} Shares")
    p2.metric("Total Capital Required", f"₹{plan['capital_required']:,.2f}", f"{plan['position_pct']}% of Account")
    p3.metric("Max Dollar Loss (Risk)", f"₹{plan['max_risk_amount']:,.2f}", f"{plan['actual_risk_pct']}% of Account")
    p4.metric("Target 1 Profit", f"₹{plan['profit_t1']:,.2f}", f"R:R {plan['rr_t1']}:1")

    if plan['position_capped_by_max_limit']:
        st.warning(f"⚠️ Quantity was automatically capped to comply with your {max_pos_pct}% maximum position size rule.")

def render_strategy_lab_tab(df: pd.DataFrame, ticker: str):
    """
    Renders Strategy Lab interactive rule builder and backtesting engine.
    """
    st.subheader("🧪 XERCES Strategy Lab — Custom Strategy Builder")
    st.caption("Construct multi-indicator algorithmic trading rules and execute realistic event-driven backtests.")

    if df is None or len(df) < 50:
        st.warning("Insufficient historical data for strategy backtesting (minimum 50 bars required).")
        return

    st.markdown("#### 1️⃣ Define Entry Rules (ANY / ALL Active Conditions)")
    
    col_e1, col_e2, col_e3 = st.columns(3)
    with col_e1:
        e_price_ema = st.checkbox("Price > EMA 20", value=True, key="lab_e_ema")
        e_ema_cross = st.checkbox("EMA 20 > EMA 50", value=True, key="lab_e_emacross")
    with col_e2:
        e_rsi_under = st.checkbox("RSI (14) < Threshold", value=False, key="lab_e_rsi_u")
        rsi_u_val = st.number_input("RSI Buy Threshold", value=45, min_value=10, max_value=60, key="lab_e_rsi_u_val")
    with col_e3:
        e_macd_pos = st.checkbox("MACD Histogram > 0", value=True, key="lab_e_macd")
        e_vol_spike = st.checkbox("Volume > 1.5x 20-day Avg", value=False, key="lab_e_vol")

    st.markdown("#### 2️⃣ Define Exit Rules & Risk Parameters")
    
    col_x1, col_x2, col_x3 = st.columns(3)
    with col_x1:
        x_rsi_over = st.checkbox("RSI (14) > Exit Threshold", value=True, key="lab_x_rsi")
        rsi_x_val = st.number_input("RSI Sell Threshold", value=70, min_value=50, max_value=90, key="lab_x_rsi_val")
    with col_x2:
        x_price_below_ema = st.checkbox("Price < EMA 20 Exit", value=True, key="lab_x_ema")
        x_macd_neg = st.checkbox("MACD Histogram < 0 Exit", value=False, key="lab_x_macd")
    with col_x3:
        sl_pct = st.slider("Fixed Stop Loss (%)", min_value=1.0, max_value=15.0, value=5.0, step=0.5, key="lab_sl")
        tp_pct = st.slider("Fixed Take Profit (%)", min_value=2.0, max_value=30.0, value=12.0, step=1.0, key="lab_tp")

    if st.button("🧪 Run Strategy Backtest", use_container_width=True, type="primary"):
        entry_conds = {
            'price_above_ema20': e_price_ema,
            'ema20_above_ema50': e_ema_cross,
            'rsi_under': e_rsi_under,
            'rsi_under_val': rsi_u_val,
            'macd_hist_positive': e_macd_pos,
            'volume_spike': e_vol_spike
        }

        exit_conds = {
            'rsi_over_exit': x_rsi_over,
            'rsi_over_exit_val': rsi_x_val,
            'price_below_ema20_exit': x_price_below_ema,
            'macd_hist_negative_exit': x_macd_neg
        }

        res = StrategyLabEngine.backtest_custom_strategy(
            df,
            entry_conditions=entry_conds,
            exit_conditions=exit_conds,
            stop_loss_pct=sl_pct,
            take_profit_pct=tp_pct
        )

        if "error" in res:
            st.error(res["error"])
            return

        st.markdown("---")
        st.markdown("#### 📈 Backtest Results & Benchmark Comparison")

        k1, k2, k3, k4, k5 = st.columns(5)
        k1.metric("Strategy Return", f"{res['total_return_pct']:+.2f}%")
        k2.metric("Buy & Hold Benchmark", f"{res['buy_hold_return_pct']:+.2f}%")
        k3.metric("Alpha (Outperformance)", f"{res['outperformance_pct']:+.2f}%")
        k4.metric("Win Rate", f"{res['win_rate_pct']}%", f"{res['total_trades']} Trades")
        k5.metric("Profit Factor", f"{res['profit_factor']}")

        # Equity Curve Chart
        fig = go.Figure()
        fig.add_trace(go.Scatter(x=res['equity_series'].index, y=res['equity_series'].values, name="Custom Strategy Equity", line=dict(color="#00e87a", width=2)))
        fig.update_layout(title="Strategy Equity Curve (₹)", template="plotly_dark", height=400)
        st.plotly_chart(fig, use_container_width=True)

        if not res['trades_df'].empty:
            st.markdown("#### 📜 Executed Trade Log")
            st.dataframe(res['trades_df'], use_container_width=True)
        else:
            st.info("No trades triggered under current rule parameters.")
