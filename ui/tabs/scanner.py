import streamlit as st
import pandas as pd
import yfinance as yf
from analytics.indicators import add_indicators, get_signal, get_signal_strength

def render_scanner_tab(SECTORS: dict, allocated_capital: float, risk_per_trade: float, risk_reward: float):
    """Render bulk multi-sector scanner tab."""
    st.markdown('<p class="section-header">[ MULTI-STOCK BULK SCANNER ]</p>', unsafe_allow_html=True)
    sc_col1, sc_col2 = st.columns([1, 1])
    with sc_col1:
        default_sector = next((k for k in SECTORS.keys() if "Banking" in k), list(SECTORS.keys())[0])
        scan_sectors = st.multiselect("Sectors", list(SECTORS.keys()), default=[default_sector])
    with sc_col2:
        scan_horizon = st.selectbox("Investment Horizon:", ["Swing Trading (1-4 Weeks)", "Short-Term Holding (1-3 Months)", "Long-Term Holding (1-5 Years)"])
        
    max_stocks = st.slider("Max stocks to scan", 10, 80, 20, step=5)

    if st.button("RUN SCAN", use_container_width=True):
        pool = []
        for sec in scan_sectors:
            pool += [(n, f"{s}.NS") for n, s in SECTORS.get(sec, [])]
        pool = pool[:max_stocks]

        if not pool:
            st.warning("No stocks in selected sectors.")
        else:
            prog = st.progress(0, text="Downloading batch data from Yahoo Finance...")
            results = []

            try:
                tickers_list = [t for _, t in pool]
                prog.progress(0.1, text=f"Fetching {len(tickers_list)} stocks in one batch...")

                batch_df = yf.download(
                    tickers_list, period="1y", interval="1d",
                    auto_adjust=True, progress=False,
                    timeout=30, group_by="ticker", threads=True
                )
                prog.progress(0.5, text="Computing indicators for each stock...")

                for idx, (name, ticker_s) in enumerate(pool):
                    try:
                        if isinstance(batch_df.columns, pd.MultiIndex):
                            if ticker_s in batch_df.columns.get_level_values(0):
                                sd = batch_df[ticker_s].copy()
                            elif ticker_s in batch_df.columns.get_level_values(1):
                                sd = batch_df.xs(ticker_s, axis=1, level=1).copy()
                            else:
                                continue
                        else:
                            sd = batch_df.copy()

                        if sd is None or sd.empty or len(sd) < 60:
                            continue

                        sd = sd.reset_index()
                        sd.columns = [str(c).strip() for c in sd.columns]
                        for col in ["Open","High","Low","Close","Volume"]:
                            if col in sd.columns:
                                sd[col] = pd.to_numeric(sd[col], errors="coerce")
                        sd = sd.dropna(subset=["Close"])
                        if len(sd) < 60:
                            continue

                        sd  = add_indicators(sd)
                        ls  = sd.iloc[-1]
                        ps  = sd.iloc[-2]
                        sig = get_signal(sd)
                        cp  = float(ls["Close"])
                        chg = (cp - float(ps["Close"])) / float(ps["Close"]) * 100
                        atr = float(ls["ATR_14"]) if pd.notna(ls.get("ATR_14")) else cp * 0.02
                        sl  = cp - atr * 1.5
                        tp  = cp + atr * 1.5 * risk_reward
                        qty = max(1, int(allocated_capital * (risk_per_trade / 100) / (atr * 1.5)))
                        rsi_v = float(ls["RSI_14"]) if pd.notna(ls.get("RSI_14")) else 50.0
                        stre = get_signal_strength(sd)
                        results.append({
                            "Stock": name, "Ticker": ticker_s.replace(".NS",""),
                            "Price": f"₹{cp:,.2f}", "1D%": f"{chg:+.2f}",
                            "RSI": f"{rsi_v:.1f}", "Signal": sig, "Strength": stre,
                            "SL": f"₹{sl:,.2f}", "Target": f"₹{tp:,.2f}", "Qty": qty,
                            "_sig": sig, "_chg": chg, "_str": stre
                        })
                    except Exception:
                        continue
                    prog.progress(0.5 + 0.5 * (idx + 1) / len(pool),
                                  text=f"Processing {idx + 1}/{len(pool)} stocks...")

            except Exception as e:
                st.warning(f"Batch download issue: {e} — try reducing the stock count.")

            prog.empty()
            if results:
                st.session_state["scan_results"] = results
                st.success(f"✅ Scan complete — {len(results)} stocks processed.")

    if st.session_state.get("scan_results"):
        res  = st.session_state["scan_results"]
        filt = st.radio("Filter", ["All", "BUY", "SELL", "HOLD", "High Strength (>=65)"], horizontal=True)
        rdf  = pd.DataFrame(res)
        if filt == "BUY":
            rdf = rdf[rdf["_sig"] == "BUY"]
        elif filt == "SELL":
            rdf = rdf[rdf["_sig"] == "SELL"]
        elif filt == "HOLD":
            rdf = rdf[rdf["_sig"] == "HOLD"]
        elif "High" in filt:
            rdf = rdf[rdf["_str"] >= 65]
        disp = rdf.drop(columns=["_sig", "_chg", "_str"], errors="ignore")
        st.dataframe(disp, use_container_width=True, hide_index=True)
        b = (rdf["_sig"] == "BUY").sum()
        s = (rdf["_sig"] == "SELL").sum()
        h = (rdf["_sig"] == "HOLD").sum()
        total_sc = b + s + h
        breadth = round(b / total_sc * 100, 1) if total_sc > 0 else 0
        st.caption(f"{len(disp)} stocks | BUY {b} | SELL {s} | HOLD {h} | Breadth {breadth}% bullish")
    else:
        st.info("Click RUN SCAN to populate.")
