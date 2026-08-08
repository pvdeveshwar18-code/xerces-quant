"""
XERCES Portfolio & Risk Management Tab Module
Includes Kelly Criterion, Risk Calculator, Black-Litterman Model, Trade Planner, Monte Carlo Stress Testing, and Portfolio Rotation Advisor.
"""

import streamlit as st
import plotly.graph_objects as go
import pandas as pd
import numpy as np
import institutional_ui as inst_ui
from risk.stress_testing import MonteCarloStressTester

def render_portfolio_tab(df, ticker: str, selected_name: str, allocated_capital: float = 100000.0):
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "🛡️ KELLY & RISK ENGINE", "🎲 MONTE CARLO STRESS TEST", "🏛️ BLACK-LITTERMAN MODEL", "📊 TRADE PLANNER", "💼 PORTFOLIO ROTATION"
    ])

    with tab1:
        inst_ui.render_risk_and_kelly_tab(df, ticker=ticker)

    with tab2:
        st.subheader("🎲 Monte Carlo Risk Stress Testing & CVaR")
        st.caption("Simulates 5,000 to 10,000 price trajectories to compute Conditional Value-at-Risk (Expected Shortfall) and historic crash drawdowns.")

        c1, c2, c3 = st.columns(3)
        sim_capital = c1.number_input("Portfolio Value (₹)", min_value=10000.0, value=float(allocated_capital), step=50000.0)
        sim_days = c2.slider("Time Horizon (Days)", min_value=10, max_value=252, value=60, step=10)
        sim_paths_count = c3.selectbox("Simulation Trajectories", [1000, 5000, 10000], index=1)

        if st.button("⚡ Execute Monte Carlo Simulation", use_container_width=True):
            with st.spinner(f"Simulating {sim_paths_count:,} trajectories over {sim_days} days..."):
                mc_res = MonteCarloStressTester.run_simulation(
                    df, portfolio_value=sim_capital, num_simulations=sim_paths_count, time_horizon_days=sim_days
                )
                st.session_state["_last_mc_res"] = mc_res

        mc_res = st.session_state.get("_last_mc_res")
        if not mc_res:
            with st.spinner("Initializing Monte Carlo stress engine..."):
                mc_res = MonteCarloStressTester.run_simulation(df, portfolio_value=sim_capital, num_simulations=2000, time_horizon_days=sim_days)
                st.session_state["_last_mc_res"] = mc_res

        if mc_res.get("error"):
            st.error(mc_res["error"])
        else:
            r1, r2, r3, r4 = st.columns(4)
            r1.metric("VaR 95% (Loss)", f"₹{mc_res['var_95_val']:,.2f}", f"-{mc_res['var_95_pct']}%")
            r2.metric("CVaR 95% (Expected Shortfall)", f"₹{mc_res['cvar_95_val']:,.2f}", f"-{mc_res['cvar_95_pct']}%")
            r3.metric("VaR 99% (Tail Risk)", f"₹{mc_res['var_99_val']:,.2f}", f"-{mc_res['var_99_pct']}%")
            r4.metric("CVaR 99% (Worst Expected Loss)", f"₹{mc_res['cvar_99_val']:,.2f}", f"-{mc_res['cvar_99_pct']}%")

            # Plot simulation paths
            paths = mc_res.get("sim_paths", np.array([]))
            if len(paths) > 0:
                fig_mc = go.Figure()
                for i in range(min(50, len(paths))):
                    fig_mc.add_trace(go.Scatter(y=paths[i], mode="lines", line=dict(width=1, color="rgba(0, 200, 255, 0.15)"), showlegend=False))
                fig_mc.update_layout(
                    title=f"Monte Carlo Simulated Trajectories (50 Sample Paths over {sim_days} Days)",
                    template="plotly_dark", height=380,
                    xaxis=dict(title="Days Ahead"), yaxis=dict(title="Portfolio Value (₹)", tickprefix="₹")
                )
                st.plotly_chart(fig_mc, use_container_width=True)

            # Historic Crash Stress Table
            st.markdown("### 💥 Historic Crash Scenario Stress Testing")
            crash_df = MonteCarloStressTester.run_crash_stress_test(portfolio_value=sim_capital, beta=1.15)
            st.dataframe(crash_df, use_container_width=True, hide_index=True)

    with tab3:
        inst_ui.render_black_litterman_tab()

    with tab4:
        inst_ui.render_trade_planner_tab(df, ticker=ticker)

    with tab5:
        st.subheader("💼 Portfolio Rotation Advisor")
        st.info("Analyzes holding assets using a 1-year ARIMA + Holt-Winters consensus forecast. Recommends rotating underperforming assets into market leaders.")
