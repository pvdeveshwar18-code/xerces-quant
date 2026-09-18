import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go

def render_backtest_tab(df: pd.DataFrame, selected_name: str, backtest_strategy: str, ensure_backtest_func):
    """Render Backtest engine tab."""
    bt_df, trades, buy_x, buy_y, sell_x, sell_y = ensure_backtest_func()
    st.markdown(f'<p class="section-header">[ BACKTEST: {backtest_strategy.upper()} — {selected_name} ]</p>', unsafe_allow_html=True)
    st.caption("Next-day open execution — no look-ahead bias.")

    if trades:
        tdf      = pd.DataFrame(trades)
        wins     = (tdf["P&L %"] > 0).sum()
        total    = len(tdf)
        win_rate = wins / total * 100
        gp       = tdf[tdf["P&L %"] > 0]["P&L %"].sum()
        gl       = abs(tdf[tdf["P&L %"] < 0]["P&L %"].sum())
        pf       = gp / gl if gl > 0 else (999.0 if gp > 0 else 0.0)
        pf_str   = f"{pf:.2f}" if gl > 0 else ("inf" if gp > 0 else "0.00")

        bt_df["Strat_Ret"] = bt_df["Signal_BT"].shift(1) * bt_df["Close"].astype(float).pct_change()
        bt_df["Equity"]    = (1 + bt_df["Strat_Ret"].fillna(0)).cumprod()
        bt_df["BH"]        = bt_df["Close"].astype(float) / float(bt_df["Close"].iloc[0])
        bt_df["Peak"]      = bt_df["Equity"].cummax()
        bt_df["DD"]        = (bt_df["Equity"] - bt_df["Peak"]) / bt_df["Peak"]
        max_dd             = abs(float(bt_df["DD"].min()) * 100)
        ret_s              = bt_df["Strat_Ret"].fillna(0)
        sharpe             = float(ret_s.mean() / ret_s.std() * np.sqrt(252)) if ret_s.std() > 0 else 0.0
        ann_ret            = (float(bt_df["Equity"].iloc[-1]) ** (252 / max(len(bt_df), 1)) - 1) * 100
        bh_ret             = (float(bt_df["BH"].iloc[-1]) - 1) * 100

        b1, b2, b3, b4, b5, b6 = st.columns(6)
        for col, lbl, val, clr in zip(
            [b1, b2, b3, b4, b5, b6],
            ["Win Rate", "Profit Factor", "Max Drawdown", "Sharpe Ratio", "Ann. Return", "Alpha vs B&H"],
            [f"{win_rate:.1f}%", pf_str, f"-{max_dd:.1f}%", f"{sharpe:.2f}",
             f"{ann_ret:+.1f}%", f"{ann_ret - bh_ret:+.1f}%"],
            ["#00e87a",
             "#00e87a" if pf >= 1.5 else "#ffcc00" if pf >= 1.0 else "#ff3355",
             "#ff3355", "#00c8ff",
             "#00e87a" if ann_ret > 0 else "#ff3355",
             "#00e87a" if ann_ret > bh_ret else "#ff3355"]
        ):
            col.markdown(
                f'<div class="glass-card"><p class="glass-label">{lbl}</p>'
                f'<div class="glass-value" style="color:{clr};font-size:1rem;">{val}</div></div>',
                unsafe_allow_html=True
            )

        fig3 = go.Figure()
        fig3.add_trace(go.Scatter(x=bt_df["Date"], y=bt_df["Equity"] * 100, name="Strategy",
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
        st.markdown('<p class="section-header">[ TRADE LOG — LAST 30 ]</p>', unsafe_allow_html=True)
        st.dataframe(tdf.tail(30), use_container_width=True, hide_index=True)
        st.download_button("Download Trade Log", tdf.to_csv(index=False).encode(),
                           f"{selected_name}_trades.csv", "text/csv")
    else:
        st.info("No signals generated. Try a different stock or strategy.")
