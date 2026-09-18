import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import xerces_plus as xp

def render_heatmap_tab(SECTORS: dict, selected_name: str, selected_ticker: str):
    """Render Sector Heatmap and 5-min Intraday candles tab."""
    st.markdown('<p class="section-header">[ 🔥 SECTOR HEATMAP — 1-DAY PERFORMANCE ]</p>', unsafe_allow_html=True)
    st.caption("Average 1-day return across a sample of stocks in each sector. Refreshed every 30 minutes.")

    with st.spinner("Computing sector performance..."):
        _sec_df = xp.compute_sector_performance(SECTORS, max_per_sector=6)

    if _sec_df is not None and not _sec_df.empty:
        _colors = ["#00e87a" if v >= 0 else "#ff3355" for v in _sec_df["Avg 1D %"]]
        fig_h = go.Figure(go.Bar(
            x=_sec_df["Avg 1D %"], y=_sec_df["Sector"], orientation="h",
            marker_color=_colors, text=[f"{v:+.2f}%" for v in _sec_df["Avg 1D %"]],
            textposition="outside", textfont=dict(color="#ddeeff", size=11)
        ))
        fig_h.update_layout(
            height=max(360, 28 * len(_sec_df)), paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#ddeeff", family="Space Mono", size=10),
            xaxis=dict(gridcolor="rgba(0,200,255,0.05)", ticksuffix="%", zerolinecolor="rgba(255,255,255,0.2)"),
            yaxis=dict(gridcolor="rgba(0,200,255,0.03)", autorange="reversed"),
            margin=dict(l=10, r=40, t=10, b=10),
        )
        st.plotly_chart(fig_h, use_container_width=True)
        st.markdown('<p class="section-header">[ SECTOR BREADTH TABLE ]</p>', unsafe_allow_html=True)
        st.dataframe(_sec_df, use_container_width=True, hide_index=True)

        _bull = int((_sec_df["Avg 1D %"] > 0).sum())
        _bear = int((_sec_df["Avg 1D %"] < 0).sum())
        _breadth = round(_bull / len(_sec_df) * 100, 1)
        _b_clr = "#00e87a" if _breadth > 60 else "#ff3355" if _breadth < 40 else "#ffcc00"
        st.markdown(
            f'<div class="glass-card"><p class="glass-label">Market Breadth</p>'
            f'<div class="glass-value" style="color:{_b_clr};font-size:1.5rem;">{_breadth}% Bullish</div>'
            f'<p style="font-size:11px;color:#6a90aa;margin-top:4px;">{_bull} sectors up · {_bear} sectors down · '
            f'Top: {_sec_df.iloc[0]["Sector"]} ({_sec_df.iloc[0]["Avg 1D %"]:+.2f}%) · '
            f'Bottom: {_sec_df.iloc[-1]["Sector"]} ({_sec_df.iloc[-1]["Avg 1D %"]:+.2f}%)</p></div>',
            unsafe_allow_html=True)
    else:
        st.warning("Could not compute sector heatmap. Try again in a moment.")

    st.markdown("---")
    st.markdown(f'<p class="section-header">[ ⏱️ INTRADAY (5-MIN) — {selected_name} ]</p>', unsafe_allow_html=True)
    _intra = xp.load_intraday(selected_ticker, interval="5m", period="5d")
    if _intra is not None and not _intra.empty:
        _tcol = "Datetime" if "Datetime" in _intra.columns else "Date"
        fig_i = go.Figure(go.Candlestick(
            x=_intra[_tcol], open=_intra["Open"], high=_intra["High"],
            low=_intra["Low"], close=_intra["Close"],
            increasing_line_color="#00e87a", decreasing_line_color="#ff3355",
            increasing_fillcolor="rgba(0,232,122,0.25)", decreasing_fillcolor="rgba(255,51,85,0.25)"
        ))
        fig_i.update_layout(
            height=380, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
            font=dict(color="#ddeeff", family="Space Mono", size=10),
            xaxis=dict(gridcolor="rgba(0,200,255,0.04)", rangeslider_visible=False),
            yaxis=dict(gridcolor="rgba(0,200,255,0.04)", tickprefix="₹"),
            margin=dict(l=10, r=10, t=15, b=10),
        )
        st.plotly_chart(fig_i, use_container_width=True)
        st.caption(f"{len(_intra)} 5-min candles over last 5 sessions.")
    else:
        st.info("Intraday data not available (indices or after-hours). Try a large-cap stock during market hours.")
