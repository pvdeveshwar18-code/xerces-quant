import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from analytics.capital_flow import compute_capital_flow

def render_inflow_outflow_tab(
    df: pd.DataFrame,
    selected_name: str,
    selected_ticker: str,
    close: float,
    currency_sym: str = "₹"
):
    """Render Capital Inflow / Outflow & Order Size Analysis tab."""
    st.markdown(f'<p class="section-header">[ 🌊 CAPITAL INFLOW / OUTFLOW & ORDER SIZE DYNAMICS — {selected_name} ]</p>', unsafe_allow_html=True)
    st.caption("Track institutional versus retail money flow, order size tier distribution, cumulative capital delta (CVD), and whale accumulation divergences.")

    if df is None or len(df) < 10:
        st.warning("Insufficient historical data to compute capital flow metrics.")
        return

    # Compute Capital Flow metrics
    flow_data = compute_capital_flow(df)
    if not flow_data:
        st.error("Failed to compute capital flow analytics.")
        return

    summary = flow_data["summary"]
    tiers = flow_data["tiers"]
    divergence = flow_data["divergence"]
    hist_df = flow_data["historical_flow_df"]

    # Section 1: KPI Top Cards
    tot_in = summary["total_inflow"]
    tot_out = summary["total_outflow"]
    net_val = summary["net_capital_flow"]
    net_pct = summary["net_flow_pct"]
    net_clr = "#00e87a" if net_val >= 0 else "#ff3355"
    net_sign = "+" if net_val >= 0 else ""

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    
    with k1:
        st.markdown(f'<div class="glass-card"><p class="glass-label">Total Inflow</p><div class="glass-value" style="color:#00e87a;">{currency_sym}{tot_in:,.0f}</div><p style="font-size:10px;color:#6a90aa;margin-top:2px;">{summary["inflow_ratio"]:.1f}% of volume</p></div>', unsafe_allow_html=True)
    with k2:
        st.markdown(f'<div class="glass-card"><p class="glass-label">Total Outflow</p><div class="glass-value" style="color:#ff3355;">{currency_sym}{tot_out:,.0f}</div><p style="font-size:10px;color:#6a90aa;margin-top:2px;">{100 - summary["inflow_ratio"]:.1f}% of volume</p></div>', unsafe_allow_html=True)
    with k3:
        st.markdown(f'<div class="glass-card"><p class="glass-label">Net Capital Flow</p><div class="glass-value" style="color:{net_clr};">{net_sign}{currency_sym}{net_val:,.0f}</div><p style="font-size:10px;color:{net_clr};margin-top:2px;">{net_sign}{net_pct:.2f}% Net</p></div>', unsafe_allow_html=True)
    with k4:
        st.markdown(f'<div class="glass-card"><p class="glass-label">Flow Sentiment</p><div class="glass-value" style="color:{summary["sentiment_color"]};font-size:0.95rem;">{summary["sentiment"]}</div><p style="font-size:10px;color:#6a90aa;margin-top:2px;">Score: {summary["flow_score"]:+d}/100</p></div>', unsafe_allow_html=True)
    with k5:
        cmf_val = summary["cmf_20"]
        cmf_clr = "#00e87a" if cmf_val > 0.05 else "#ff3355" if cmf_val < -0.05 else "#ffcc00"
        st.markdown(f'<div class="glass-card"><p class="glass-label">Chaikin MF (20)</p><div class="glass-value" style="color:{cmf_clr};">{cmf_val:+.3f}</div><p style="font-size:10px;color:#6a90aa;margin-top:2px;">{"Accumulation" if cmf_val>0 else "Distribution"}</p></div>', unsafe_allow_html=True)
    with k6:
        mfi_val = summary["mfi_14"]
        mfi_clr = "#ff3355" if mfi_val > 80 else "#00e87a" if mfi_val < 20 else "#00c8ff"
        st.markdown(f'<div class="glass-card"><p class="glass-label">MFI (14)</p><div class="glass-value" style="color:{mfi_clr};">{mfi_val:.1f}</div><p style="font-size:10px;color:#6a90aa;margin-top:2px;">{"Overbought" if mfi_val>80 else "Oversold" if mfi_val<20 else "Balanced"}</p></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Section 2: Smart Money Divergence Alert Banner
    st.markdown(f"""
<div class="glass-card" style="border-left: 4px solid {divergence['color']}; padding: 12px 16px; margin-bottom: 16px;">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="font-family:'Orbitron',sans-serif; font-weight:700; color:#ddeeff; font-size:14px;">📡 SMART MONEY FLOW DIVERGENCE: {divergence['type']}</span>
        <span style="font-family:'Space Mono',monospace; font-size:11px; font-weight:bold; color:{divergence['color']};">INSTITUTIONAL SIGNAL</span>
    </div>
    <div style="margin-top:6px; font-family:'Space Mono',monospace; font-size:12px; color:#a0aec0; line-height:1.5;">
        {divergence['description']}
    </div>
</div>
""", unsafe_allow_html=True)

    # Section 3: Order Size Flow Matrix
    st.markdown('<p class="section-header">[ 📊 ORDER SIZE TIER BREAKDOWN ]</p>', unsafe_allow_html=True)
    
    tier_rows = []
    for tier_name, tinfo in tiers.items():
        t_net = tinfo["net"]
        t_clr = "#00e87a" if t_net >= 0 else "#ff3355"
        tier_rows.append({
            "Tier": tinfo["tier_label"],
            "Turnover Share": f"{tinfo['share_pct']:.1f}%",
            f"Inflow ({currency_sym})": f"{currency_sym}{tinfo['inflow']:,.0f}",
            f"Outflow ({currency_sym})": f"{currency_sym}{tinfo['outflow']:,.0f}",
            f"Net Flow ({currency_sym})": f"{'+' if t_net>=0 else ''}{currency_sym}{t_net:,.0f}",
            "Status": "🟢 Net Buyer" if t_net >= 0 else "🔴 Net Seller"
        })
    st.dataframe(pd.DataFrame(tier_rows), use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Section 4: Interactive Charts
    col_c1, col_c2 = st.columns([1.2, 1])

    with col_c1:
        # Side-by-side Inflow vs Outflow Bar Chart by Tier
        fig_bars = go.Figure()
        tier_names = list(tiers.keys())
        inflows = [tiers[t]["inflow"] for t in tier_names]
        outflows = [tiers[t]["outflow"] for t in tier_names]

        fig_bars.add_trace(go.Bar(
            name="Inflow (Buying)",
            x=tier_names,
            y=inflows,
            marker=dict(color="#00e87a"),
            text=[f"{currency_sym}{v/1e5:.1f}L" if currency_sym=="₹" else f"${v/1e3:.1f}K" for v in inflows],
            textposition="auto"
        ))
        fig_bars.add_trace(go.Bar(
            name="Outflow (Selling)",
            x=tier_names,
            y=outflows,
            marker=dict(color="#ff3355"),
            text=[f"{currency_sym}{v/1e5:.1f}L" if currency_sym=="₹" else f"${v/1e3:.1f}K" for v in outflows],
            textposition="auto"
        ))
        fig_bars.update_layout(
            title=dict(text="Order Size Inflow vs. Outflow", font=dict(color="#00c8ff", size=13)),
            barmode="group",
            height=320,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#ddeeff", family="Space Mono", size=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis=dict(gridcolor="rgba(0,200,255,0.05)", title=f"Volume Turnover ({currency_sym})"),
            xaxis=dict(gridcolor="rgba(0,200,255,0.05)"),
            margin=dict(l=10, r=10, t=40, b=10)
        )
        st.plotly_chart(fig_bars, use_container_width=True)

    with col_c2:
        # Donut Chart: Inflow Distribution across order sizes
        fig_donut = make_subplots(rows=1, cols=2, specs=[[{"type": "domain"}, {"type": "domain"}]],
                                  subplot_titles=["Inflow Allocation", "Outflow Allocation"])

        colors = ["#00c8ff", "#00e87a", "#ffcc00", "#ff66aa"]
        fig_donut.add_trace(go.Pie(
            labels=tier_names,
            values=inflows,
            name="Inflow",
            hole=0.55,
            marker=dict(colors=colors),
            textinfo="percent"
        ), 1, 1)

        fig_donut.add_trace(go.Pie(
            labels=tier_names,
            values=outflows,
            name="Outflow",
            hole=0.55,
            marker=dict(colors=colors),
            textinfo="percent"
        ), 1, 2)

        fig_donut.update_layout(
            title=dict(text="Capital Share by Tier", font=dict(color="#00c8ff", size=13)),
            height=320,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#ddeeff", family="Space Mono", size=10),
            showlegend=True,
            legend=dict(orientation="h", yanchor="bottom", y=-0.15, xanchor="center", x=0.5),
            margin=dict(l=10, r=10, t=40, b=30)
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    # Section 5: Cumulative Net Capital Flow (CVD Timeline) vs Price Action
    st.markdown('<p class="section-header">[ 📈 CUMULATIVE CAPITAL FLOW & SMART MONEY CVD TIMELINE ]</p>', unsafe_allow_html=True)
    
    # 60-day or available lookback
    plot_sub = hist_df.iloc[-90:] if len(hist_df) > 90 else hist_df
    plot_dates = plot_sub["Date"] if "Date" in plot_sub.columns else plot_sub.index

    fig_cvd = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.55, 0.45],
        subplot_titles=[f"{selected_name} Price Action", "Cumulative Capital Flow & Institutional Net Delta"]
    )

    # Row 1: Price Action
    fig_cvd.add_trace(go.Candlestick(
        x=plot_dates,
        open=plot_sub["Open"],
        high=plot_sub["High"],
        low=plot_sub["Low"],
        close=plot_sub["Close"],
        name="Price",
        increasing_line_color="#00e87a",
        decreasing_line_color="#ff3355"
    ), row=1, col=1)

    # Row 2: Cumulative Net Flows
    fig_cvd.add_trace(go.Scatter(
        x=plot_dates,
        y=plot_sub["Cum_Smart_Money_Net"],
        name="Smart Money Net (XL + Large)",
        line=dict(color="#00c8ff", width=2.5),
        mode="lines"
    ), row=2, col=1)

    fig_cvd.add_trace(go.Scatter(
        x=plot_dates,
        y=plot_sub["Cum_Net_Flow"],
        name="Total Net Capital Flow",
        line=dict(color="#9955ff", width=1.5, dash="dot"),
        mode="lines"
    ), row=2, col=1)

    fig_cvd.add_trace(go.Scatter(
        x=plot_dates,
        y=plot_sub["Cum_Retail_Net"],
        name="Retail Net Flow (Small)",
        line=dict(color="#ffcc00", width=1.5),
        mode="lines"
    ), row=2, col=1)

    fig_cvd.update_layout(
        height=520,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ddeeff", family="Space Mono", size=10),
        xaxis_rangeslider_visible=False,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        yaxis=dict(gridcolor="rgba(0,200,255,0.05)", title="Price"),
        yaxis2=dict(gridcolor="rgba(0,200,255,0.05)", title=f"Cumulative Flow ({currency_sym})"),
        xaxis2=dict(gridcolor="rgba(0,200,255,0.05)"),
        margin=dict(l=10, r=10, t=30, b=10)
    )
    st.plotly_chart(fig_cvd, use_container_width=True)

    # Section 6: 1-Click Order Execution on Flow Signal
    st.markdown("---")
    st.markdown('<p class="section-header">[ ⚡ 1-CLICK BROKER EXECUTION ON FLOW SIGNAL ]</p>', unsafe_allow_html=True)
    st.caption("Capitalize on detected whale accumulation or distribution instantly across your connected broker accounts.")

    col_e1, col_e2, col_e3, col_e4 = st.columns([1.2, 1, 1, 1.2])
    with col_e1:
        selected_broker = st.selectbox(
            "Broker Route:",
            ["Kotak Neo (NSE/BSE)", "Zerodha Kite Connect", "Angel One SmartAPI", "Upstox Developer API", "Alpaca US Trading"],
            key="brk_sel_inflow"
        )
    with col_e2:
        recommended_side = "BUY" if summary["flow_score"] > 0 else "SELL"
        side_sel = st.selectbox("Action:", ["BUY", "SELL"], index=0 if recommended_side=="BUY" else 1, key="side_sel_inflow")
    with col_e3:
        exec_qty = st.number_input("Quantity:", min_value=1, value=10, step=1, key="qty_sel_inflow")
    with col_e4:
        st.markdown("<div style='height:28px;'></div>", unsafe_allow_html=True)
        if st.button("🚀 EXECUTE FLOW ORDER", use_container_width=True, key="exec_flow_order_btn"):
            with st.spinner(f"Routing {side_sel} order for {selected_ticker} to {selected_broker}..."):
                try:
                    from brokers.executor import execute_order
                    res = execute_order(
                        broker_name=selected_broker,
                        symbol=selected_ticker,
                        transaction_type=side_sel,
                        quantity=exec_qty,
                        price=close
                    )
                    st.success(f"✅ {res['message']}")
                    st.info(f"Order ID: `{res['order_id']}` | Status: `{res['status']}` | Broker: `{res['broker']}`")
                except Exception as e:
                    st.error(f"Execution Error: {e}")
