import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def render_backtest_tab(df: pd.DataFrame, selected_name: str, backtest_strategy: str, ensure_backtest_func):
    """Render Backtest engine tab with Indian regulatory friction & institutional diagnostics."""
    bt_df, trades, buy_x, buy_y, sell_x, sell_y = ensure_backtest_func()
    st.markdown(f'<p class="section-header">[ BACKTEST: {backtest_strategy.upper()} — {selected_name} ]</p>', unsafe_allow_html=True)
    st.caption("Next-day open execution · Full Indian market taxes (STT, GST, Stamp Duty, Brokerage) & execution slippage modeled.")

    if trades:
        tdf = pd.DataFrame(trades)
        pnl_col = "Net P&L %" if "Net P&L %" in tdf.columns else "P&L %"
        wins = (tdf[pnl_col] > 0).sum()
        total = len(tdf)
        win_rate = (wins / total * 100) if total > 0 else 0.0

        gp = tdf[tdf[pnl_col] > 0][pnl_col].sum()
        gl = abs(tdf[tdf[pnl_col] < 0][pnl_col].sum())
        pf = gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0)
        pf_str = f"{pf:.2f}" if gl > 0 else ("inf" if gp > 0 else "0.00")

        total_friction = tdf["Friction & Tax ₹"].sum() if "Friction & Tax ₹" in tdf.columns else 0.0

        bt_df["Strat_Ret"] = bt_df["Signal_BT"].shift(1) * bt_df["Close"].astype(float).pct_change()
        bt_df["Equity"] = (1 + bt_df["Strat_Ret"].fillna(0)).cumprod()
        bt_df["BH"] = bt_df["Close"].astype(float) / float(bt_df["Close"].iloc[0])
        bt_df["Peak"] = bt_df["Equity"].cummax()
        bt_df["DD"] = (bt_df["Equity"] - bt_df["Peak"]) / bt_df["Peak"]
        max_dd = abs(float(bt_df["DD"].min()) * 100)
        ret_s = bt_df["Strat_Ret"].fillna(0)
        sharpe = float(ret_s.mean() / ret_s.std() * np.sqrt(252)) if ret_s.std() > 0 else 0.0
        ann_ret = (float(bt_df["Equity"].iloc[-1]) ** (252 / max(len(bt_df), 1)) - 1) * 100
        bh_ret = (float(bt_df["BH"].iloc[-1]) - 1) * 100

        b1, b2, b3, b4, b5, b6 = st.columns(6)
        for col, lbl, val, clr in zip(
            [b1, b2, b3, b4, b5, b6],
            ["Win Rate (Net)", "Profit Factor", "Total Taxes/Friction", "Max Drawdown", "Ann. Return", "Alpha vs B&H"],
            [f"{win_rate:.1f}%", pf_str, f"₹{total_friction:,.0f}", f"-{max_dd:.1f}%",
             f"{ann_ret:+.1f}%", f"{ann_ret - bh_ret:+.1f}%"],
            ["#00e87a" if win_rate >= 50 else "#ffcc00",
             "#00e87a" if pf >= 1.5 else "#ffcc00" if pf >= 1.0 else "#ff3355",
             "#ffcc00", "#ff3355",
             "#00e87a" if ann_ret > 0 else "#ff3355",
             "#00e87a" if ann_ret > bh_ret else "#ff3355"]
        ):
            col.markdown(
                f'<div class="glass-card"><p class="glass-label">{lbl}</p>'
                f'<div class="glass-value" style="color:{clr};font-size:1rem;">{val}</div></div>',
                unsafe_allow_html=True
            )

        st.markdown("""
        <div style="background:rgba(0,200,255,0.06);border-left:3px solid #00c8ff;padding:8px 12px;border-radius:4px;font-size:11px;color:#a0aec0;margin:6px 0 12px 0;">
        ⚡ <b>Institutional Friction Model:</b> Deducts STT (0.1% buy + 0.1% sell for delivery), NSE Turnover Fees (0.00345%), GST (18%), Stamp Duty, Brokerage (₹20/order), and 5 bps execution slippage.
        </div>
        """, unsafe_allow_html=True)

        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=bt_df["Date"], y=bt_df["Equity"] * 100, name="Strategy (Gross)",
                                  line=dict(color="#00e87a", width=2)))
        fig3.add_trace(go.Scatter(x=bt_df["Date"], y=bt_df["BH"] * 100, name="Buy & Hold",
                                  line=dict(color="#7c6ef8", width=1.5, dash="dot")))
        fig3.update_layout(
            height=280, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#ddeeff", family="Space Mono", size=10),
            xaxis=dict(gridcolor="rgba(0,200,255,0.04)"),
            yaxis=dict(gridcolor="rgba(0,200,255,0.04)", ticksuffix="%"),
            margin=dict(l=10, r=10, t=15, b=10),
            legend=dict(bgcolor="rgba(7,18,32,0.5)", bordercolor="rgba(0,200,255,0.15)", borderwidth=1)
        )
        st.plotly_chart(fig3, use_container_width=True)

        st.markdown('<p class="section-header">[ DETAILED TRADE LOG — LAST 30 EXECUTIONS ]</p>', unsafe_allow_html=True)
        st.dataframe(tdf.tail(30), use_container_width=True, hide_index=True)
        st.download_button("Download Trade Log (CSV)", tdf.to_csv(index=False).encode(),
                           f"{selected_name}_trades_friction_analyzed.csv", "text/csv")

        st.markdown("---")
        st.markdown('<p class="section-header">[ ⚡ STRATEGY AUTO-TRADER & LIVE ROUTING DESK ]</p>', unsafe_allow_html=True)
        st.caption("Arm this backtested strategy to generate bracket orders and route live/paper execution to connected brokers.")

        from analytics.strategy_bot import evaluate_live_strategy_signal, deploy_strategy_signal
        live_eval = evaluate_live_strategy_signal(df, strategy_name=backtest_strategy)

        col_sig1, col_sig2, col_sig3, col_sig4 = st.columns(4)
        sig_action = live_eval["action"]
        sig_clr = "#00e87a" if sig_action == "BUY" else "#ff3355" if sig_action == "SELL" else "#ffcc00"

        with col_sig1:
            st.markdown(f'<div class="glass-card"><p class="glass-label">Active Signal (Current Bar)</p><div class="glass-value" style="color:{sig_clr};">{sig_action}</div><p style="font-size:10px;color:#6a90aa;margin-top:2px;">Strength: {live_eval["strength"]}/100</p></div>', unsafe_allow_html=True)
        with col_sig2:
            st.markdown(f'<div class="glass-card"><p class="glass-label">Entry Reference</p><div class="glass-value" style="color:#ddeeff;">₹{live_eval["entry_price"]:,.2f}</div><p style="font-size:10px;color:#6a90aa;margin-top:2px;">RSI: {live_eval["rsi"]}</p></div>', unsafe_allow_html=True)
        with col_sig3:
            st.markdown(f'<div class="glass-card"><p class="glass-label">Dynamic Stop-Loss</p><div class="glass-value" style="color:#ff3355;">₹{live_eval["stop_loss"]:,.2f}</div><p style="font-size:10px;color:#ff3355;margin-top:2px;">Risk: ₹{live_eval["risk_per_share"]:.2f}/sh</p></div>', unsafe_allow_html=True)
        with col_sig4:
            st.markdown(f'<div class="glass-card"><p class="glass-label">Take-Profit Target</p><div class="glass-value" style="color:#00e87a;">₹{live_eval["take_profit"]:,.2f}</div><p style="font-size:10px;color:#00e87a;margin-top:2px;">R:R 1:{live_eval["risk_reward"]:.1f}</p></div>', unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background:rgba(7,18,32,0.5);border-left:3px solid {sig_clr};padding:8px 12px;border-radius:4px;font-size:12px;color:#ddeeff;margin:8px 0 14px 0;">
        <b>Signal Rationale:</b> {live_eval["rationale"]}
        </div>
        """, unsafe_allow_html=True)

        col_dep1, col_dep2, col_dep3, col_dep4 = st.columns([1.2, 1, 1, 1.2])
        with col_dep1:
            dep_broker = st.selectbox("Execution Broker:", ["Kotak Neo (NSE/BSE)", "Zerodha Kite Connect", "Angel One SmartAPI", "Upstox Developer API", "Alpaca US Trading"], key=f"bt_dep_brk_{selected_name}")
        with col_dep2:
            dep_action = st.selectbox("Action:", ["BUY", "SELL"], index=0 if sig_action == "BUY" else 1, key=f"bt_dep_act_{selected_name}")
        with col_dep3:
            dep_qty = st.number_input("Deploy Quantity:", min_value=1, value=10, step=1, key=f"bt_dep_qty_{selected_name}")
        with col_dep4:
            st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
            if st.button("🚀 DEPLOY STRATEGY ORDER", use_container_width=True, key=f"bt_dep_btn_{selected_name}"):
                with st.spinner(f"Routing {dep_action} strategy signal via {dep_broker}..."):
                    try:
                        res = deploy_strategy_signal(
                            broker_name=dep_broker,
                            symbol=selected_name,
                            action=dep_action,
                            quantity=dep_qty,
                            price=live_eval["entry_price"],
                            stop_loss=live_eval["stop_loss"],
                            take_profit=live_eval["take_profit"]
                        )
                        st.success(f"✅ {res.get('message', 'Strategy order deployed successfully!')}")
                        st.info(f"Order ID: `{res.get('order_id')}` | Status: `{res.get('status')}` | SL: ₹{live_eval['stop_loss']} | TP: ₹{live_eval['take_profit']}")
                    except Exception as e:
                        st.error(f"Execution Error: {e}")
    else:
        st.info("No signals generated. Try a different stock or strategy.")
