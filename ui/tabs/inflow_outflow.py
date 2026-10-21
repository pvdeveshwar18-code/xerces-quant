import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from analytics.capital_flow import compute_capital_flow
from data.loader import load_intraday, get_sector_peers, load_ohlcv

def render_inflow_outflow_tab(
    df: pd.DataFrame,
    selected_name: str,
    selected_ticker: str,
    close: float,
    currency_sym: str = "₹"
):
    """Render Institutional-Grade Capital Inflow / Outflow & Order Size Analysis tab."""
    st.markdown(f'<p class="section-header">[ 🌊 CAPITAL INFLOW / OUTFLOW & ORDER SIZE DYNAMICS — {selected_name} ]</p>', unsafe_allow_html=True)
    st.caption("Institutional versus retail money flow, order size tier distribution, cumulative capital delta (CVD), price-level footprint, and whale accumulation divergences.")

    if df is None or len(df) < 5:
        st.warning("Insufficient historical data to compute capital flow metrics.")
        return

    # Section 0: Controls (Resolution & Timeframe)
    ctrl_col1, ctrl_col2 = st.columns([1, 1.5])
    with ctrl_col1:
        res_mode = st.radio(
            "Data Stream Resolution:",
            ["Daily / Swing Tape", "5-Min Intraday Tape"],
            horizontal=True,
            key="flow_res_mode"
        )
    with ctrl_col2:
        timeframe_sel = st.radio(
            "Aggregation Horizon:",
            ["1D (Today)", "5D (Weekly)", "20D (1-Month)", "60D (Quarterly)", "Full History"],
            horizontal=True,
            index=0,
            key="flow_timeframe_sel"
        )

    # Determine dataset based on resolution mode
    active_df = df
    if res_mode == "5-Min Intraday Tape":
        with st.spinner("Fetching 5-minute intraday tick tape..."):
            intra_df = load_intraday(selected_ticker, interval="5m", period="5d")
            if intra_df is not None and len(intra_df) >= 10:
                active_df = intra_df
            else:
                st.info("Intraday 5m tape unavailable; falling back to Daily Swing tape.")

    # Compute Capital Flow metrics
    flow_data = compute_capital_flow(active_df)
    if not flow_data:
        st.error("Failed to compute capital flow analytics.")
        return

    tf_map = {
        "1D (Today)": "1D",
        "5D (Weekly)": "5D",
        "20D (1-Month)": "20D",
        "60D (Quarterly)": "60D",
        "Full History": "All"
    }
    tf_key = tf_map.get(timeframe_sel, "1D")
    
    # Active summary and tiers for selected timeframe
    summary = flow_data["timeframes"].get(tf_key, flow_data["summary"])
    tiers = summary.get("tiers", flow_data["tiers"])
    divergence = flow_data["divergence"]
    hist_df = flow_data["historical_flow_df"]
    price_levels = flow_data.get("price_levels", pd.DataFrame())

    # Section 1: Top KPI Metric Cards
    tot_in = summary["total_inflow"]
    tot_out = summary["total_outflow"]
    net_val = summary["net_capital_flow"]
    net_pct = summary["net_flow_pct"]
    net_clr = "#00e87a" if net_val >= 0 else "#ff3355"
    net_sign = "+" if net_val >= 0 else ""

    sm_net = summary["smart_money_net"]
    sm_ratio = summary.get("smart_money_ratio", 50.0)
    ret_net = summary["retail_net"]
    ret_ratio = summary.get("retail_ratio", 50.0)

    k1, k2, k3, k4, k5, k6 = st.columns(6)
    
    with k1:
        st.markdown(f'<div class="glass-card"><p class="glass-label">Total Inflow ({tf_key})</p><div class="glass-value" style="color:#00e87a;">{currency_sym}{tot_in:,.0f}</div><p style="font-size:10px;color:#6a90aa;margin-top:2px;">{summary["inflow_ratio"]:.1f}% of volume</p></div>', unsafe_allow_html=True)
    with k2:
        st.markdown(f'<div class="glass-card"><p class="glass-label">Total Outflow ({tf_key})</p><div class="glass-value" style="color:#ff3355;">{currency_sym}{tot_out:,.0f}</div><p style="font-size:10px;color:#6a90aa;margin-top:2px;">{100 - summary["inflow_ratio"]:.1f}% of volume</p></div>', unsafe_allow_html=True)
    with k3:
        st.markdown(f'<div class="glass-card"><p class="glass-label">Net Capital Flow</p><div class="glass-value" style="color:{net_clr};">{net_sign}{currency_sym}{net_val:,.0f}</div><p style="font-size:10px;color:{net_clr};margin-top:2px;">{net_sign}{net_pct:.2f}% Net</p></div>', unsafe_allow_html=True)
    with k4:
        st.markdown(f'<div class="glass-card"><p class="glass-label">Whale Net (XL+L)</p><div class="glass-value" style="color:{"#00e87a" if sm_net>=0 else "#ff3355"};">{"+" if sm_net>=0 else ""}{currency_sym}{sm_net:,.0f}</div><p style="font-size:10px;color:#6a90aa;margin-top:2px;">Conviction: {sm_ratio:.1f}% Buy</p></div>', unsafe_allow_html=True)
    with k5:
        st.markdown(f'<div class="glass-card"><p class="glass-label">Retail Net (Small)</p><div class="glass-value" style="color:{"#00e87a" if ret_net>=0 else "#ff3355"};">{"+" if ret_net>=0 else ""}{currency_sym}{ret_net:,.0f}</div><p style="font-size:10px;color:#6a90aa;margin-top:2px;">Conviction: {ret_ratio:.1f}% Buy</p></div>', unsafe_allow_html=True)
    with k6:
        st.markdown(f'<div class="glass-card"><p class="glass-label">Flow Sentiment</p><div class="glass-value" style="color:{summary["sentiment_color"]};font-size:0.95rem;">{summary["sentiment"]}</div><p style="font-size:10px;color:#6a90aa;margin-top:2px;">Score: {summary["flow_score"]:+d}/100</p></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Section 2: Smart Money Divergence Alert Banner
    st.markdown(f"""
<div class="glass-card" style="border-left: 4px solid {divergence['color']}; padding: 12px 16px; margin-bottom: 16px;">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="font-family:'Orbitron',sans-serif; font-weight:700; color:#ddeeff; font-size:14px;">📡 SMART MONEY FLOW RADAR: {divergence['type']}</span>
        <span style="font-family:'Space Mono',monospace; font-size:11px; font-weight:bold; color:{divergence['color']};">INSTITUTIONAL SIGNAL</span>
    </div>
    <div style="margin-top:6px; font-family:'Space Mono',monospace; font-size:12px; color:#a0aec0; line-height:1.5;">
        {divergence['description']}
    </div>
</div>
""", unsafe_allow_html=True)

    # Section 3: Order Size Flow Matrix
    st.markdown(f'<p class="section-header">[ 📊 ORDER SIZE TIER BREAKDOWN — {timeframe_sel} ]</p>', unsafe_allow_html=True)
    
    tier_rows = []
    for tier_name, tinfo in tiers.items():
        t_net = tinfo["net"]
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

    # Section 4: Interactive Order Size Charts
    col_c1, col_c2 = st.columns([1.2, 1])

    with col_c1:
        # Grouped Bar Chart: Inflow vs Outflow by Tier
        fig_bars = go.Figure()
        tier_names = list(tiers.keys())
        inflows = [tiers[t]["inflow"] for t in tier_names]
        outflows = [tiers[t]["outflow"] for t in tier_names]

        fmt_factor = 1e5 if currency_sym == "₹" else 1e3
        fmt_unit = "L" if currency_sym == "₹" else "K"

        fig_bars.add_trace(go.Bar(
            name="Inflow (Buying)",
            x=tier_names,
            y=inflows,
            marker=dict(color="#00e87a"),
            text=[f"{currency_sym}{v/fmt_factor:.1f}{fmt_unit}" for v in inflows],
            textposition="auto"
        ))
        fig_bars.add_trace(go.Bar(
            name="Outflow (Selling)",
            x=tier_names,
            y=outflows,
            marker=dict(color="#ff3355"),
            text=[f"{currency_sym}{v/fmt_factor:.1f}{fmt_unit}" for v in outflows],
            textposition="auto"
        ))
        fig_bars.update_layout(
            title=dict(text=f"Order Size Inflow vs. Outflow ({timeframe_sel})", font=dict(color="#00c8ff", size=13)),
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
        # Donut Chart: Inflow Allocation vs Outflow Allocation
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
    
    plot_sub = hist_df.iloc[-90:] if len(hist_df) > 90 else hist_df
    plot_dates = plot_sub["Date"] if "Date" in plot_sub.columns else plot_sub.index

    fig_cvd = make_subplots(
        rows=2, cols=1,
        shared_xaxes=True,
        vertical_spacing=0.06,
        row_heights=[0.55, 0.45],
        subplot_titles=[f"{selected_name} Price Action", "Cumulative Capital Flow & Institutional Net Delta"]
    )

    # Row 1: Candlestick Price Action
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

    # Row 2: Cumulative Flow Lines
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
        height=500,
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

    # Section 6: Daily Net Capital Flow Bar Delta & Price Footprint Profile
    col_d1, col_d2 = st.columns([1.2, 1])

    with col_d1:
        st.markdown('<p class="section-header">[ 📊 DAILY NET FLOW DELTA & 10D SIGNAL ]</p>', unsafe_allow_html=True)
        recent_sub = hist_df.iloc[-30:] if len(hist_df) > 30 else hist_df
        r_dates = recent_sub["Date"] if "Date" in recent_sub.columns else recent_sub.index
        net_bars = recent_sub["Net_Capital_Flow"]
        bar_colors = ["#00e87a" if v >= 0 else "#ff3355" for v in net_bars]
        ma_net = net_bars.rolling(10, min_periods=1).mean()

        fig_delta = go.Figure()
        fig_delta.add_trace(go.Bar(
            x=r_dates,
            y=net_bars,
            marker_color=bar_colors,
            name="Daily Net Flow"
        ))
        fig_delta.add_trace(go.Scatter(
            x=r_dates,
            y=ma_net,
            name="10D Signal Trend",
            line=dict(color="#00c8ff", width=2)
        ))
        fig_delta.update_layout(
            height=320,
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#ddeeff", family="Space Mono", size=10),
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
            yaxis=dict(gridcolor="rgba(0,200,255,0.05)", title=f"Net Delta ({currency_sym})"),
            xaxis=dict(gridcolor="rgba(0,200,255,0.05)"),
            margin=dict(l=10, r=10, t=30, b=10)
        )
        st.plotly_chart(fig_delta, use_container_width=True)

    with col_d2:
        st.markdown('<p class="section-header">[ 🎯 PRICE LEVEL FOOTPRINT PROFILE ]</p>', unsafe_allow_html=True)
        if not price_levels.empty:
            fig_fp = go.Figure()
            fig_fp.add_trace(go.Bar(
                y=price_levels["price_mid"],
                x=price_levels["inflow"],
                orientation="h",
                name="Inflow (Demand)",
                marker_color="#00e87a"
            ))
            fig_fp.add_trace(go.Bar(
                y=price_levels["price_mid"],
                x=-price_levels["outflow"],
                orientation="h",
                name="Outflow (Supply)",
                marker_color="#ff3355"
            ))
            # Point of Control annotation
            poc_row = price_levels[price_levels["is_poc"]]
            if not poc_row.empty:
                poc_price = float(poc_row["price_mid"].iloc[0])
                fig_fp.add_hline(y=poc_price, line_dash="dash", line_color="#ffcc00",
                                 annotation_text=f"POC: {currency_sym}{poc_price:,.1f}",
                                 annotation_position="bottom right")

            fig_fp.update_layout(
                barmode="overlay",
                height=320,
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#ddeeff", family="Space Mono", size=10),
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
                xaxis=dict(gridcolor="rgba(0,200,255,0.05)", title="Outflow ◄ | ► Inflow"),
                yaxis=dict(gridcolor="rgba(0,200,255,0.05)", title="Price Level"),
                margin=dict(l=10, r=10, t=30, b=10)
            )
            st.plotly_chart(fig_fp, use_container_width=True)
        else:
            st.info("Price footprint profile unavailable.")

    # Section 7: Sector Whale Radar (Compare Inflow across Peers)
    with st.expander("📡  Sector Whale Radar: Compare Capital Inflows across Peers", expanded=False):
        st.caption("Scans and ranks sector peers side-by-side to detect where institutional capital is rotating.")
        sector_name, peers = get_sector_peers(selected_ticker, max_peers=4)
        
        if peers:
            radar_tickers = [selected_ticker] + [p for p in peers if p != selected_ticker]
            radar_rows = []
            
            for tkr in radar_tickers:
                peer_df = df if tkr == selected_ticker else load_ohlcv(tkr, period="1mo")
                if peer_df is not None and len(peer_df) >= 5:
                    p_res = compute_capital_flow(peer_df)
                    if p_res:
                        p_sum = p_res["summary"]
                        p_div = p_res["divergence"]
                        p_close = float(peer_df["Close"].iloc[-1])
                        p_net = p_sum["net_capital_flow"]
                        p_sm = p_sum["smart_money_net"]
                        radar_rows.append({
                            "Ticker": tkr,
                            "Last Price": f"{currency_sym}{p_close:,.2f}",
                            f"Total Net ({currency_sym})": f"{'+' if p_net>=0 else ''}{currency_sym}{p_net:,.0f}",
                            f"Whale Net ({currency_sym})": f"{'+' if p_sm>=0 else ''}{currency_sym}{p_sm:,.0f}",
                            "Whale Conviction": f"{p_sum.get('smart_money_ratio', 50.0):.1f}%",
                            "Flow Sentiment": p_sum["sentiment"],
                            "Radar Signal": p_div["type"]
                        })

            if radar_rows:
                radar_table = pd.DataFrame(radar_rows)
                st.dataframe(radar_table, use_container_width=True, hide_index=True)
        else:
            st.info("No sector peers identified for this asset.")

    # Section 8: Export & 1-Click Order Execution Bridge
    st.markdown("---")
    st.markdown('<p class="section-header">[ ⚡ 1-CLICK BROKER EXECUTION & DATA EXPORT ]</p>', unsafe_allow_html=True)
    st.caption("Capitalize on detected whale accumulation or export calculated order flow data for quantitative research.")

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

    # Export CSV
    export_df = hist_df[["Close", "Volume", "Turnover", "Total_Inflow", "Total_Outflow",
                         "Net_Capital_Flow", "XL_Net", "L_Net", "M_Net", "S_Net",
                         "Cum_Net_Flow", "Cum_Smart_Money_Net", "Cum_Retail_Net",
                         "CMF_20", "MFI_14"]].copy()
    csv_bytes = export_df.to_csv().encode("utf-8")
    st.download_button(
        label="⬇️ Download Complete Inflow/Outflow Dataset (CSV)",
        data=csv_bytes,
        file_name=f"{selected_ticker}_inflow_outflow_flow.csv",
        mime="text/csv",
        use_container_width=True
    )
