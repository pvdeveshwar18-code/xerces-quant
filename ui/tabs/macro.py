"""
XERCES Macro Overview Tab
Renders market indices telemetry and embeds the Tableau Macro Dashboard.
"""

import streamlit as st
import plotly.graph_objects as go
from data.market_data import load_indices
from ui.components.tableau_macro import render_tableau_macro_dashboard

def render_macro_tab():
    st.markdown('<h2 class="xerces-title" style="font-size:1.5rem;margin-bottom:12px;">📊 LIVE MARKET OVERVIEW</h2>', unsafe_allow_html=True)
    with st.spinner("Loading market indices telemetry..."):
        idx_data = load_indices()

    INDEX_META = [
        ("^NSEI", "NIFTY 50", "#00e87a"), ("^NSEBANK", "BANK NIFTY", "#00c8ff"),
        ("^BSESN", "SENSEX", "#ffcc00"),  ("^CRSMID", "NIFTY MIDCAP", "#ff6b35"),
        ("^CNXSC", "NIFTY SMALLCAP", "#7c6ef8"), ("^INDIAVIX", "INDIA VIX", "#ff3355"),
    ]
    cols = st.columns(6)
    for col, (sym, name, clr) in zip(cols, INDEX_META):
        try:
            idf = idx_data.get(sym)
            if idf is None or len(idf) < 2:
                col.warning(name); continue
            cv = float(idf["Close"].iloc[-1])
            pv = float(idf["Close"].iloc[-2])
            chg = (cv - pv) / pv * 100.0
            flip = sym == "^INDIAVIX"
            cclr = ("#ff3355" if chg >= 0 else "#00e87a") if flip else ("#00e87a" if chg >= 0 else "#ff3355")
            arrow = "▲" if chg >= 0 else "▼"
            col.markdown(f"""<div class="glass-card">
                <p class="glass-label" style="color:{clr};">{name}</p>
                <div class="glass-value" style="font-size:1.1rem;">{cv:,.2f}</div>
                <p style="font-size:11px;color:{cclr};margin:2px 0;font-weight:600;">{arrow} {abs(chg):.2f}%</p>
            </div>""", unsafe_allow_html=True)
        except Exception:
            col.warning(name)

    # NIFTY 50 sparkline
    try:
        n50 = idx_data.get("^NSEI")
        if n50 is not None and not n50.empty:
            fig0 = go.Figure()
            fig0.add_trace(go.Scatter(x=n50["Date"], y=n50["Close"], line=dict(color="#00e87a", width=2), name="Nifty 50", fill="tozeroy", fillcolor="rgba(0,232,122,0.04)"))
            fig0.update_layout(
                height=220, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#ddeeff", family="Space Mono", size=10), margin=dict(l=10, r=10, t=10, b=10),
                xaxis=dict(gridcolor="rgba(0,200,255,0.05)"), yaxis=dict(gridcolor="rgba(0,200,255,0.05)", tickprefix="₹"),
                showlegend=False
            )
            st.plotly_chart(fig0, use_container_width=True)
    except Exception:
        pass

    st.markdown("<br>", unsafe_allow_html=True)
    render_tableau_macro_dashboard()
