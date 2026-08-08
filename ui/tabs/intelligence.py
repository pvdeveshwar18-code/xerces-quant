"""
XERCES Market Intelligence Tab Module
Includes Bulk Sector Scanner (with ML probabilities), Heatmap, Stock Compare, Options Chain & Max Pain, and FII/DII Cash Flows.
"""

import streamlit as st
import pandas as pd
import xerces_plus as xp
from data.market_data import fetch_fii_dii, fetch_options_chain, parse_fii_dii, parse_options_chain
from ai_committee.ml_classifier import MLSignalClassifier
from ui.search import SECTORS
from data.market_data import load_ohlcv, add_indicators

def render_intelligence_tab(ticker: str, selected_name: str, current_close: float = 0.0):
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "📡 BULK SCANNER", "🔥 SECTOR HEATMAP", "🔄 STOCK COMPARE", "🎯 OPTIONS CHAIN", "📊 FII/DII FLOWS"
    ])

    with tab1:
        st.subheader("📡 Bulk Sector Scanner (ML Powered)")
        st.caption("Scan stocks across 18 sectors for active technical & ML signals.")

        sec_choice = st.selectbox("Select Sector Universe", list(SECTORS.keys()))
        stocks_in_sec = SECTORS[sec_choice]

        if st.button(f"🔍 Scan {sec_choice} ({len(stocks_in_sec)} Stocks)", use_container_width=True):
            scan_results = []
            progress_bar = st.progress(0)
            for idx, (name, sym) in enumerate(stocks_in_sec[:20]): # Scan top 20 stocks in selected sector
                full_sym = f"{sym}.NS"
                raw_df = load_ohlcv(full_sym, period="6m")
                if raw_df is not None and len(raw_df) >= 40:
                    ind_df = add_indicators(raw_df)
                    ml_res = MLSignalClassifier.train_and_predict(ind_df)
                    close_p = float(ind_df["Close"].iloc[-1])
                    rsi_v = float(ind_df["RSI_14"].iloc[-1]) if "RSI_14" in ind_df else 50.0
                    chg_v = float(ind_df["Return"].iloc[-1] * 100.0) if "Return" in ind_df else 0.0

                    scan_results.append({
                        "Stock": name,
                        "Symbol": sym,
                        "Price (₹)": round(close_p, 2),
                        "1D %": round(chg_v, 2),
                        "RSI": round(rsi_v, 1),
                        "ML Signal": ml_res["signal"],
                        "ML Confidence": f"{ml_res['confidence']}%",
                        "BUY Prob": f"{ml_res['buy_prob']}%",
                        "SELL Prob": f"{ml_res['sell_prob']}%"
                    })
                progress_bar.progress((idx + 1) / min(20, len(stocks_in_sec)))
            
            st.session_state["_last_scan_df"] = pd.DataFrame(scan_results)

        scan_df = st.session_state.get("_last_scan_df")
        if scan_df is not None and not scan_df.empty:
            st.dataframe(scan_df, use_container_width=True, hide_index=True)

    with tab2:
        xp.render_heatmap_tab()

    with tab3:
        xp.render_compare_tab()

    with tab4:
        st.subheader(f"🎯 Options Chain & Max Pain — {selected_name} ({ticker})")
        with st.spinner("Fetching live NSE Option Chain..."):
            opt_data = fetch_options_chain(ticker)

        if opt_data:
            chain_df, pcr, max_pain, exp_date = parse_options_chain(opt_data, current_close)
            if pcr is not None:
                o1, o2, o3 = st.columns(3)
                o1.metric("Put-Call Ratio (PCR)", pcr)
                o2.metric("Max Pain Strike", f"₹{max_pain:,.2f}")
                o3.metric("Nearest Expiry", exp_date)
            if chain_df is not None and not chain_df.empty:
                st.dataframe(chain_df, use_container_width=True, hide_index=True)
            else:
                st.info("Live options chain telemetry loaded (No active expiry rows).")
        else:
            st.info("Option chain unavailable for this ticker or market closed.")

    with tab5:
        st.subheader("📊 Institutional FII / DII Net Cash Flows")
        with st.spinner("Fetching FII/DII daily cash flow data..."):
            fii_raw = fetch_fii_dii()

        if fii_raw:
            fii_df, latest_row = parse_fii_dii(fii_raw)
            if fii_df is not None and not fii_df.empty:
                st.dataframe(fii_df, use_container_width=True, hide_index=True)
            else:
                st.info("FII/DII data format unavailable.")
        else:
            st.info("FII/DII flow service unavailable.")

