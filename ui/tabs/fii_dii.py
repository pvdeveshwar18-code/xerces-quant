import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data.loader import fetch_fii_dii, parse_fii_dii

def render_fii_dii_tab():
    """Render FII / DII institutional flow data tab."""
    st.markdown('<p class="section-header">[ 📊 FII / DII INSTITUTIONAL FLOW — NSE INDIA ]</p>', unsafe_allow_html=True)
    st.caption("Foreign Institutional Investor & Domestic Institutional Investor daily net activity. Source: NSE India.")

    with st.spinner("Fetching FII/DII data from NSE India..."):
        fii_data = fetch_fii_dii()
        df_fii, today_fii = parse_fii_dii(fii_data)

    if df_fii is not None and today_fii is not None:
        fii_net = float(today_fii["FII Net"])
        dii_net = float(today_fii["DII Net"])
        fii_clr = "#00e87a" if fii_net >= 0 else "#ff3355"
        dii_clr = "#00e87a" if dii_net >= 0 else "#ff3355"
        combined = fii_net + dii_net
        comb_clr = "#00e87a" if combined >= 0 else "#ff3355"

        f1, f2, f3, f4 = st.columns(4)
        for col, lbl, val, clr in zip([f1,f2,f3,f4],
            ["FII Net Today (Cr)", "DII Net Today (Cr)", "Combined Net (Cr)", "Date"],
            [f"{'▲' if fii_net>=0 else '▼'} ₹{abs(fii_net):,.0f}",
             f"{'▲' if dii_net>=0 else '▼'} ₹{abs(dii_net):,.0f}",
             f"{'▲' if combined>=0 else '▼'} ₹{abs(combined):,.0f}",
             str(today_fii["Date"])[:10]],
            [fii_clr, dii_clr, comb_clr, "#ddeeff"]):
            col.markdown(f'<div class="glass-card"><p class="glass-label">{lbl}</p>'
                         f'<div class="glass-value" style="color:{clr};font-size:1.1rem;">{val}</div></div>',
                         unsafe_allow_html=True)

        sentiment_fii = "BULLISH" if fii_net > 0 else "BEARISH"
        sent_clr_fii  = "#00e87a" if fii_net > 0 else "#ff3355"
        if fii_net > 0 and dii_net > 0:
            market_view = "Both FII and DII are buying — strong institutional conviction. Typically bullish for markets."
        elif fii_net > 0 and dii_net < 0:
            market_view = "FII buying, DII selling — foreign money flowing in, domestic institutions taking profit."
        elif fii_net < 0 and dii_net > 0:
            market_view = "FII selling, DII buying — domestic institutions absorbing foreign outflows. Market resilient."
        else:
            market_view = "Both FII and DII selling — broad institutional outflow. Typically bearish for near-term."

        st.markdown(f'''<div class="glass-card" style="margin:10px 0;">
            <p class="glass-label">Market Interpretation</p>
            <div style="font-size:13px;color:{sent_clr_fii};font-weight:600;margin:4px 0;">{sentiment_fii} INSTITUTIONAL FLOW</div>
            <p style="font-size:12px;color:#a0aec0;margin:4px 0;line-height:1.6;">{market_view}</p>
        </div>''', unsafe_allow_html=True)

        if len(df_fii) > 1:
            st.markdown('<p class="section-header">[ RECENT FII / DII DAILY NET FLOWS ]</p>', unsafe_allow_html=True)
            fig_fii = go.Figure()
            fii_colors = ["#00e87a" if v >= 0 else "#ff3355" for v in df_fii["FII Net"]]
            dii_colors = ["#00c8ff" if v >= 0 else "#ff6b35" for v in df_fii["DII Net"]]
            fig_fii.add_trace(go.Bar(x=df_fii["Date"], y=df_fii["FII Net"], name="FII Net",
                marker_color=fii_colors, opacity=0.85))
            fig_fii.add_trace(go.Bar(x=df_fii["Date"], y=df_fii["DII Net"], name="DII Net",
                marker_color=dii_colors, opacity=0.85))
            fig_fii.add_hline(y=0, line_color="rgba(255,255,255,0.2)", line_width=1)
            fig_fii.update_layout(
                height=320, barmode="group",
                paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#ddeeff", family="Space Mono", size=10),
                xaxis=dict(gridcolor="rgba(0,200,255,0.04)"),
                yaxis=dict(gridcolor="rgba(0,200,255,0.04)", title="Net Flow (Cr ₹)"),
                margin=dict(l=10,r=10,t=15,b=10),
                legend=dict(bgcolor="rgba(7,18,32,0.5)", bordercolor="rgba(0,200,255,0.15)", borderwidth=1)
            )
            st.plotly_chart(fig_fii, use_container_width=True)

        st.markdown('<p class="section-header">[ DETAILED FLOW TABLE ]</p>', unsafe_allow_html=True)
        disp_fii = df_fii[["Date","FII Buy","FII Sell","FII Net","DII Buy","DII Sell","DII Net"]].copy()
        disp_fii = disp_fii.round(2)
        st.dataframe(disp_fii, use_container_width=True, hide_index=True)
        st.download_button("⬇️ Download FII/DII Data",
                           disp_fii.to_csv(index=False).encode(),
                           "fii_dii_flows.csv", "text/csv")
    else:
        st.warning("Could not fetch FII/DII data from NSE India. NSE may be blocking automated requests.")
        st.info("**Why this happens:** NSE India requires cookie-based session authentication. The data is available at nseindia.com → Market Data → FII/DII Activity.")
        st.markdown('''<div class="glass-card">
            <p class="section-header" style="margin-top:0;">Understanding FII / DII Flows</p>
            <div style="font-size:12px;color:#a0aec0;line-height:1.8;">
            <b style="color:#00c8ff;">FII (Foreign Institutional Investors)</b> — Foreign funds, hedge funds, sovereign wealth funds. 
            Their buying/selling drives large directional moves in Nifty 50. FII net positive = bullish signal.<br><br>
            <b style="color:#00c8ff;">DII (Domestic Institutional Investors)</b> — Indian mutual funds, insurance companies (LIC), banks. 
            Often act as a counterbalance — they buy when FIIs sell, providing market support.<br><br>
            <b style="color:#ffcc00;">Key Rule:</b> When both FII and DII are net buyers, markets tend to rally strongly. 
            When both are sellers, expect sharp corrections. FII flows dominate short-term direction.
            </div>
        </div>''', unsafe_allow_html=True)
