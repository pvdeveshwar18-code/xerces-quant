import json
import streamlit as st
import pandas as pd
import xerces_plus as xp
from data.loader import fetch_fundamentals, fetch_news

def render_export_tab(df: pd.DataFrame, selected_name: str, selected_ticker: str, trades: list = None):
    """Render PDF & Excel Reports Generator tab."""
    st.markdown(f'<p class="section-header">[ 📄 EXPORT REPORTS — {selected_name} ]</p>', unsafe_allow_html=True)
    st.caption("Generate a shareable PDF report or Excel workbook with all analytics on this stock.")

    ec1, ec2 = st.columns(2)

    with ec1:
        st.markdown('<div class="glass-card">'
                    '<p class="glass-label">📄 PDF STOCK REPORT</p>'
                    '<div class="glass-value" style="color:#00c8ff;font-size:1.1rem;">One-page analyst report</div>'
                    '<p style="font-size:11px;color:#6a90aa;margin-top:6px;">'
                    'Includes KPIs, fundamentals, and (optional) AI-generated trade thesis + news summary.'
                    '</p></div>', unsafe_allow_html=True)
        _use_ai = st.checkbox("Include AI thesis & news summary (uses LLM key)", value=False, key="pdf_ai")
        if st.button("🖨️ Generate PDF Report", use_container_width=True, key="pdf_gen"):
            with st.spinner("Building PDF..."):
                _ctx_pdf = dict(st.session_state.get("_stock_ctx", {}))
                _f_data, _ = fetch_fundamentals(selected_ticker)
                _ctx_pdf["fundamentals"] = _f_data or {}
                _thesis_txt = ""; _news_txt = ""
                if _use_ai:
                    _ctx_pdf["news"] = [x.get("title","") for x in (fetch_news(selected_ticker, selected_name) or [])[:10]]
                    _thesis_txt = xp.ai_trade_thesis(_ctx_pdf)
                    _news_txt   = xp.ai_summarize_news(_ctx_pdf["news"], selected_name)
                _pdf = xp.build_pdf_report(_ctx_pdf, _thesis_txt, _news_txt)
                st.session_state["_last_pdf"] = _pdf
                st.session_state["_last_pdf_name"] = f"{selected_name}_xerces_report.pdf"
        if st.session_state.get("_last_pdf"):
            st.download_button("⬇️ Download PDF",
                st.session_state["_last_pdf"], st.session_state["_last_pdf_name"],
                "application/pdf", use_container_width=True, key="pdf_dl")

    with ec2:
        st.markdown('<div class="glass-card">'
                    '<p class="glass-label">📊 EXCEL WORKBOOK</p>'
                    '<div class="glass-value" style="color:#00e87a;font-size:1.1rem;">Multi-sheet analytics</div>'
                    '<p style="font-size:11px;color:#6a90aa;margin-top:6px;">'
                    'Sheets: OHLCV + indicators, backtest trades, scanner results (if available), '
                    'trade journal, watchlist.'
                    '</p></div>', unsafe_allow_html=True)
        if st.button("📗 Generate Excel Workbook", use_container_width=True, key="xls_gen"):
            with st.spinner("Building Excel..."):
                _sheets = {
                    "OHLCV_Indicators": df[[c for c in ["Date","Open","High","Low","Close","Volume",
                                                        "SMA_20","SMA_50","SMA_200","RSI_14","MACD",
                                                        "MACD_Signal","ATR_14","Volatility_20"] if c in df.columns]].copy(),
                }
                if trades:
                    _sheets["Backtest_Trades"] = pd.DataFrame(trades)
                if st.session_state.get("scan_results"):
                    _sc = pd.DataFrame(st.session_state["scan_results"]).drop(
                        columns=["_sig","_chg","_str"], errors="ignore")
                    _sheets["Scanner_Results"] = _sc
                _jdf = xp.load_journal()
                if not _jdf.empty: _sheets["Journal"] = _jdf
                _wl = xp.load_watchlist()
                if _wl: _sheets["Watchlist"] = pd.DataFrame(_wl)
                _xbytes = xp.build_excel_bytes(_sheets)
                st.session_state["_last_xls"] = _xbytes
                st.session_state["_last_xls_name"] = f"{selected_name}_xerces.xlsx"
        if st.session_state.get("_last_xls"):
            st.download_button("⬇️ Download Excel",
                st.session_state["_last_xls"], st.session_state["_last_xls_name"],
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                use_container_width=True, key="xls_dl")

    st.markdown('<p class="section-header" style="margin-top:20px;">[ QUICK EXPORTS ]</p>', unsafe_allow_html=True)
    q1, q2, q3 = st.columns(3)
    q1.download_button("⬇️ Chart Data CSV",
        df.to_csv(index=False).encode(), f"{selected_name}_ohlcv.csv", "text/csv",
        use_container_width=True, key="q1_dl")
    if trades:
        q2.download_button("⬇️ Backtest Trades",
            pd.DataFrame(trades).to_csv(index=False).encode(),
            f"{selected_name}_trades.csv", "text/csv",
            use_container_width=True, key="q2_dl")
    _wl = xp.load_watchlist()
    if _wl:
        q3.download_button("⬇️ Watchlist JSON",
            json.dumps(_wl, indent=2).encode(), "xerces_watchlist.json",
            "application/json", use_container_width=True, key="q3_dl")
