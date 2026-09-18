import streamlit as st
from data.loader import fetch_fundamentals

def render_fundamentals_tab(selected_name: str, selected_ticker: str):
    """Render Fundamental Analysis tab from Screener.in."""
    st.markdown(f'<p class="section-header">[ 📋 FUNDAMENTAL ANALYSIS — {selected_name} ]</p>', unsafe_allow_html=True)
    st.caption("Key financial ratios from Screener.in. Refreshed daily.")

    with st.spinner(f"Fetching fundamentals for {selected_name}..."):
        fund_data, fund_url = fetch_fundamentals(selected_ticker)

    if fund_data and any(v is not None for v in fund_data.values()):
        cols_f = st.columns(3)
        ratio_keys = [("P/E Ratio","#00c8ff"),("P/B Ratio","#ffcc00"),("ROE (%)","#00e87a"),
                      ("ROCE (%)","#00e87a"),("Debt/Equity","#ff3355"),("Div Yield (%)","#7c4dff")]
        for i, (key, clr) in enumerate(ratio_keys):
            val = fund_data.get(key)
            val_str = f"{val:.2f}" if val is not None else "N/A"
            cols_f[i % 3].markdown(
                f'<div class="glass-card"><p class="glass-label">{key}</p>'
                f'<div class="glass-value" style="color:{clr};">{val_str}</div></div>',
                unsafe_allow_html=True
            )

        ep1, ep2 = st.columns(2)
        eps  = fund_data.get("EPS (TTM)")
        prom = fund_data.get("Promoter Holding", fund_data.get("Promoter Hold%"))
        ep1.markdown(
            f'<div class="glass-card"><p class="glass-label">EPS (TTM)</p>'
            f'<div class="glass-value" style="color:#fbbf24;">{"₹"+str(round(eps,2)) if eps else "N/A"}</div></div>',
            unsafe_allow_html=True)
        ep2.markdown(
            f'<div class="glass-card"><p class="glass-label">Promoter Holding</p>'
            f'<div class="glass-value" style="color:{"#00e87a" if prom and prom>50 else "#ffcc00" if prom else "#6a90aa"};">{""+str(round(prom,1))+"%" if prom else "N/A"}</div></div>',
            unsafe_allow_html=True)

        pe  = fund_data.get("P/E Ratio")
        roe = fund_data.get("ROE (%)")
        de  = fund_data.get("Debt/Equity")
        scores = []
        if pe:  scores.append("Cheap" if pe < 15 else "Fair" if pe < 30 else "Expensive")
        if roe: scores.append("High ROE" if roe > 20 else "Moderate ROE" if roe > 12 else "Low ROE")
        if de:  scores.append("Low Debt" if de < 0.5 else "Moderate Debt" if de < 1.5 else "High Debt")
        if scores:
            verdict_text = " | ".join(scores)
            verdict_clr  = "#00e87a" if "Cheap" in verdict_text or "High ROE" in verdict_text else "#ffcc00"
            st.markdown(f'<div class="glass-card"><p class="glass-label">Fundamental Verdict</p>'
                        f'<p style="font-size:13px;color:{verdict_clr};font-weight:600;margin:4px 0;">{verdict_text}</p></div>',
                        unsafe_allow_html=True)

        st.caption("Data source: Screener.in · Refreshed daily · Garbage/out-of-range values are filtered")
        st.markdown(f"[View full analysis on Screener.in]({fund_url})")
    else:
        st.warning(f"Could not fetch fundamental data for {selected_name} from Screener.in.")
        st.info("Screener.in covers most NSE-listed companies. Try large-cap stocks like RELIANCE, TCS, HDFCBANK.")

    with st.expander("📖 Ratio interpretation guide"):
        st.markdown("""
| Ratio | Good | Average | Expensive/Risky |
|---|---|---|---|
| P/E | < 15 | 15–30 | > 40 |
| P/B | < 1.5 | 1.5–4 | > 6 |
| ROE | > 20% | 12–20% | < 10% |
| ROCE | > 20% | 12–20% | < 10% |
| Debt/Equity | < 0.5 | 0.5–1.5 | > 2.0 |
| Promoter Hold | > 50% | 35–50% | < 25% |

**Indian Market Context:** Nifty 50 trades at avg P/E of ~22. Premium growth stocks (Titan, Asian Paints) command 60–80x P/E. PSU banks trade at 5–10x. Always compare within the same sector.
""")
