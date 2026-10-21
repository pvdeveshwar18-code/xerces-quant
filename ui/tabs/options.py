import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.loader import fetch_options_chain, parse_options_chain

def render_options_tab(selected_name: str, selected_ticker: str, close: float):
    """Render Options Chain, PCR & Max Pain analysis tab."""
    st.markdown(f'<p class="section-header">[ 🎯 OPTIONS CHAIN — {selected_name} ]</p>', unsafe_allow_html=True)
    st.caption("NSE India options data. Works for Nifty 50 stocks with active F&O contracts.")

    with st.spinner(f"Fetching options chain for {selected_name}..."):
        opt_data = fetch_options_chain(selected_ticker)
        df_chain, pcr, max_pain, expiry = parse_options_chain(opt_data, close)

    if df_chain is not None and len(df_chain) > 0:
        o1, o2, o3, o4 = st.columns(4)
        pcr_clr  = "#00e87a" if pcr and pcr > 1 else "#ff3355" if pcr and pcr < 0.7 else "#ffcc00"
        pain_clr = "#00c8ff"
        updown   = "Above" if close > (max_pain or close) else "Below"
        pct_from_pain = abs(close - max_pain) / max_pain * 100 if max_pain else 0

        for col, lbl, val, clr in zip([o1,o2,o3,o4],
            ["Spot Price","Max Pain","Put/Call Ratio","Expiry"],
            [f"₹{close:,.2f}", f"₹{max_pain:,.0f}" if max_pain else "N/A",
             f"{pcr:.3f}" if pcr else "N/A", str(expiry) if expiry else "N/A"],
            ["#ddeeff", pain_clr, pcr_clr, "#6a90aa"]):
            col.markdown(f'<div class="glass-card"><p class="glass-label">{lbl}</p>'
                         f'<div class="glass-value" style="color:{clr};font-size:1.1rem;">{val}</div></div>',
                         unsafe_allow_html=True)

        if pcr:
            if pcr > 1.2:
                pcr_interp = "HIGH PCR (>1.2) — Bearish sentiment dominant. Contrarian signal: markets may be oversold, potential reversal up."
                pi_clr = "#00e87a"
            elif pcr < 0.7:
                pcr_interp = "LOW PCR (<0.7) — Bullish sentiment dominant. Contrarian signal: markets may be overbought, potential pullback."
                pi_clr = "#ff3355"
            else:
                pcr_interp = "NEUTRAL PCR (0.7–1.2) — Balanced put/call activity. No extreme sentiment reading."
                pi_clr = "#ffcc00"
            st.markdown(f'<div class="glass-card"><p class="glass-label">PCR Interpretation</p>'
                        f'<p style="font-size:12px;color:{pi_clr};margin:4px 0;font-weight:600;">{pcr_interp}</p></div>',
                        unsafe_allow_html=True)

        if max_pain:
            mp_interp = f"Spot (₹{close:,.0f}) is {updown} max pain (₹{max_pain:,.0f}) by {pct_from_pain:.1f}%. Option sellers profit most if expiry is at ₹{max_pain:,.0f}. Gravitational pull toward max pain as expiry approaches."
            st.markdown(f'<div class="glass-card"><p class="glass-label">Max Pain Analysis</p>'
                        f'<p style="font-size:12px;color:#a0aec0;margin:4px 0;line-height:1.6;">{mp_interp}</p></div>',
                        unsafe_allow_html=True)

        st.markdown('<p class="section-header">[ OPEN INTEREST BY STRIKE ]</p>', unsafe_allow_html=True)
        spot_strikes = df_chain[(df_chain["Strike"] >= close * 0.85) & (df_chain["Strike"] <= close * 1.15)]
        if len(spot_strikes) > 0:
            fig_oi = go.Figure()
            fig_oi.add_trace(go.Bar(x=spot_strikes["Strike"], y=spot_strikes["CE OI"],
                name="Call OI", marker_color="rgba(255,51,85,0.7)"))
            fig_oi.add_trace(go.Bar(x=spot_strikes["Strike"], y=spot_strikes["PE OI"],
                name="Put OI", marker_color="rgba(0,200,255,0.7)"))
            if max_pain:
                fig_oi.add_vline(x=max_pain, line_dash="dash", line_color="#fbbf24",
                    annotation_text=f"Max Pain ₹{max_pain:,.0f}", annotation_font_color="#fbbf24")
            fig_oi.add_vline(x=close, line_dash="dot", line_color="rgba(255,255,255,0.5)",
                annotation_text=f"Spot ₹{close:,.0f}", annotation_font_color="#ddeeff")
            fig_oi.update_layout(
                height=360, barmode="group",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#ddeeff", family="Space Mono", size=10),
                xaxis=dict(title="Strike Price", gridcolor="rgba(0,200,255,0.04)"),
                yaxis=dict(title="Open Interest", gridcolor="rgba(0,200,255,0.04)"),
                margin=dict(l=10,r=10,t=15,b=10),
                legend=dict(bgcolor="rgba(7,18,32,0.5)", bordercolor="rgba(0,200,255,0.15)", borderwidth=1)
            )
            st.plotly_chart(fig_oi, use_container_width=True)

        st.markdown('<p class="section-header">[ FULL OPTIONS CHAIN TABLE ]</p>', unsafe_allow_html=True)
        from analytics.options_greeks import enrich_options_chain_with_greeks
        df_chain_greeks = enrich_options_chain_with_greeks(df_chain, spot_price=close, days_to_expiry=7)

        col_oc1, col_oc2 = st.columns([1, 2])
        with col_oc1:
            show_greeks = st.checkbox("Show Black-Scholes Greeks (Delta, Theta, Gamma, Vega)", value=True, key="opt_greeks_table_chk")

        if show_greeks:
            chain_cols = ["CE Delta", "CE Theta", "CE LTP", "CE OI", "CE IV", "Strike", "PE IV", "PE OI", "PE LTP", "PE Theta", "PE Delta"]
        else:
            chain_cols = ["CE LTP", "CE OI", "CE IV", "Strike", "PE IV", "PE OI", "PE LTP"]

        chain_disp = df_chain_greeks[[c for c in chain_cols if c in df_chain_greeks.columns]].copy()
        chain_disp["ATM"] = df_chain["Strike"].apply(lambda s: "◀ ATM" if abs(s - close) == df_chain["Strike"].apply(lambda x: abs(x-close)).min() else "")
        st.dataframe(chain_disp.round(2), use_container_width=True, hide_index=True)
        st.download_button("⬇️ Download Options Chain",
                           chain_disp.round(2).to_csv(index=False).encode(),
                           f"{selected_name}_options_chain.csv", "text/csv")
    else:
        st.warning(f"Options chain not available for {selected_name}.")
        st.info("Options data is available only for stocks in the NSE F&O segment (Nifty 50 and select mid-caps). NSE may also block automated access.")
        st.markdown('''<div class="glass-card">
            <p class="section-header" style="margin-top:0;">Options Chain Concepts</p>
            <div style="font-size:12px;color:#a0aec0;line-height:1.8;">
            <b style="color:#00c8ff;">Max Pain</b> — The strike price where option buyers lose the most money at expiry. 
            Due to gamma exposure, stock prices tend to gravitate toward max pain as expiry approaches.<br><br>
            <b style="color:#00c8ff;">Put/Call Ratio (PCR)</b> — Total Put OI divided by Total Call OI. 
            PCR > 1.2 = bearish sentiment (contrarian buy signal). PCR < 0.7 = bullish sentiment (contrarian sell signal).<br><br>
            <b style="color:#00c8ff;">Open Interest (OI)</b> — Number of outstanding contracts. High OI at a strike = strong support/resistance level.<br><br>
            <b style="color:#00c8ff;">Implied Volatility (IV)</b> — Market expectation of future price movement. High IV = expensive options = expected big move.
            </div>
        </div>''', unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<p class="section-header">[ 📊 MULTI-LEG OPTIONS STRATEGY PAYOFF VISUALIZER & GREEKS ]</p>', unsafe_allow_html=True)
    st.caption("Simulate multi-leg options strategies, payoff diagrams, T+0 curves, and Net Black-Scholes Greeks.")
    
    col_opt1, col_opt2 = st.columns([1, 1.6])
    with col_opt1:
        opt_strat = st.selectbox(
            "Options Strategy:",
            ["Bull Call Spread", "Bear Put Spread", "Iron Condor", "Long Straddle", "Long Strangle", "Covered Call", "Protective Put"],
            key="opt_strat_sel"
        )
        opt_dte = st.slider("Days to Expiration (DTE):", 1, 60, 30, key="opt_dte_sel")
        opt_iv = st.slider("Implied Volatility (IV %):", 10, 100, 25, step=5, key="opt_iv_sel") / 100.0

    with col_opt2:
        try:
            from ui.tabs.options_visualizer import generate_payoff_diagram
            fig_payoff, metrics = generate_payoff_diagram(spot_price=close, strategy=opt_strat, dte=opt_dte, iv=opt_iv)
            st.plotly_chart(fig_payoff, use_container_width=True)
        except Exception as e:
            st.warning(f"Payoff diagram error: {e}")
            metrics = None

    if metrics:
        m1, m2, m3, m4, m5 = st.columns(5)
        with m1:
            st.markdown(f'<div class="glass-card"><p class="glass-label">Max Profit</p><div class="glass-value" style="color:#00e87a;">₹{metrics["max_profit"]:,.1f}</div><p style="font-size:10px;color:#6a90aa;margin-top:2px;">Per share</p></div>', unsafe_allow_html=True)
        with m2:
            st.markdown(f'<div class="glass-card"><p class="glass-label">Max Loss</p><div class="glass-value" style="color:#ff3355;">₹{metrics["max_loss"]:,.1f}</div><p style="font-size:10px;color:#6a90aa;margin-top:2px;">Per share</p></div>', unsafe_allow_html=True)
        with m3:
            rr_str = f"1 : {metrics['risk_reward']:.2f}" if metrics['risk_reward'] < 100 else "Unlimited"
            st.markdown(f'<div class="glass-card"><p class="glass-label">Risk:Reward</p><div class="glass-value" style="color:#00c8ff;">{rr_str}</div><p style="font-size:10px;color:#6a90aa;margin-top:2px;">Payoff profile</p></div>', unsafe_allow_html=True)
        with m4:
            be_str = ", ".join(f"₹{b:,.1f}" for b in metrics["breakevens"]) if metrics["breakevens"] else "None"
            st.markdown(f'<div class="glass-card"><p class="glass-label">Breakevens</p><div class="glass-value" style="color:#ffcc00;font-size:1rem;">{be_str}</div><p style="font-size:10px;color:#6a90aa;margin-top:2px;">Zero P&L target</p></div>', unsafe_allow_html=True)
        with m5:
            st.markdown(f'<div class="glass-card"><p class="glass-label">Net Delta (Δ)</p><div class="glass-value" style="color:{"#00e87a" if metrics["net_delta"]>=0 else "#ff3355"};">{metrics["net_delta"]:+.3f}</div><p style="font-size:10px;color:#6a90aa;margin-top:2px;">Directional bias</p></div>', unsafe_allow_html=True)

        g1, g2, g3 = st.columns(3)
        with g1:
            st.markdown(f'<div class="glass-card"><p class="glass-label">Net Gamma (Γ)</p><div class="glass-value" style="color:#00c8ff;">{metrics["net_gamma"]:.5f}</div></div>', unsafe_allow_html=True)
        with g2:
            st.markdown(f'<div class="glass-card"><p class="glass-label">Net Theta (Θ)</p><div class="glass-value" style="color:{"#00e87a" if metrics["net_theta"]>=0 else "#ff3355"};">{metrics["net_theta"]:+.2f} ₹/day</div></div>', unsafe_allow_html=True)
        with g3:
            st.markdown(f'<div class="glass-card"><p class="glass-label">Net Vega (ν)</p><div class="glass-value" style="color:#ffcc00;">{metrics["net_vega"]:+.2f} ₹/1% IV</div></div>', unsafe_allow_html=True)
