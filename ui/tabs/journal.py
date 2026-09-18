import datetime
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import xerces_plus as xp

def render_journal_tab(selected_name: str, close: float, backtest_strategy: str):
    """Render Trade Journal tab."""
    st.markdown('<p class="section-header">[ 📓 MY TRADE JOURNAL ]</p>', unsafe_allow_html=True)
    st.caption("Log actual trades to track your real P&L and strategy performance. Saved to disk.")

    _j = xp.load_journal()

    with st.expander("➕ Add trade entry", expanded=(_j.empty)):
        jc1, jc2, jc3 = st.columns(3)
        with jc1:
            _jdate = st.date_input("Date", value=datetime.date.today(), key="j_date")
            _jtick = st.text_input("Ticker", value=selected_name.upper(), key="j_tick")
            _jside = st.selectbox("Side", ["LONG","SHORT"], key="j_side")
        with jc2:
            _jqty  = st.number_input("Qty", min_value=1, value=10, key="j_qty")
            _jent  = st.number_input("Entry ₹", min_value=0.0, value=round(close, 2), step=0.5, key="j_ent")
            _jexit = st.number_input("Exit ₹ (0 if open)", min_value=0.0, value=0.0, step=0.5, key="j_exit")
        with jc3:
            _jstrat = st.text_input("Strategy", value=backtest_strategy, key="j_strat")
            _jnotes = st.text_area("Notes", height=80, key="j_notes")

        if st.button("💾 Save Trade", use_container_width=True, key="j_save"):
            _sign = 1 if _jside == "LONG" else -1
            _pnl_val = (_jexit - _jent) * _jqty * _sign if _jexit > 0 else 0.0
            _pnl_pct = ((_jexit - _jent) / _jent * 100 * _sign) if _jexit > 0 and _jent > 0 else 0.0
            _row = {"Date": str(_jdate), "Ticker": _jtick, "Side": _jside,
                    "Qty": _jqty, "Entry": _jent, "Exit": _jexit,
                    "P&L (₹)": round(_pnl_val, 2), "P&L %": round(_pnl_pct, 2),
                    "Strategy": _jstrat, "Notes": _jnotes}
            _j = pd.concat([_j, pd.DataFrame([_row])], ignore_index=True)
            xp.save_journal(_j)
            st.success(f"Trade saved. Total: {len(_j)} entries.")
            st.rerun()

    if not _j.empty:
        _closed = _j[_j["Exit"].astype(float) > 0]
        _tot_pnl = float(_closed["P&L (₹)"].astype(float).sum()) if not _closed.empty else 0.0
        _win = int((_closed["P&L (₹)"].astype(float) > 0).sum()) if not _closed.empty else 0
        _tot = len(_closed)
        _wr  = round(_win / _tot * 100, 1) if _tot > 0 else 0.0

        jk1, jk2, jk3, jk4 = st.columns(4)
        for col, lbl, val, clr in zip(
            [jk1,jk2,jk3,jk4],
            ["Total Trades","Closed","Win Rate","Total P&L"],
            [str(len(_j)), str(_tot), f"{_wr}%", f"₹{_tot_pnl:,.2f}"],
            ["#00c8ff","#ddeeff","#00e87a" if _wr >= 50 else "#ff3355",
             "#00e87a" if _tot_pnl >= 0 else "#ff3355"]
        ):
            col.markdown(f'<div class="glass-card"><p class="glass-label">{lbl}</p>'
                         f'<div class="glass-value" style="color:{clr};font-size:1.2rem;">{val}</div></div>',
                         unsafe_allow_html=True)

        st.markdown('<p class="section-header">[ TRADE HISTORY (editable) ]</p>', unsafe_allow_html=True)
        _edited = st.data_editor(_j, use_container_width=True, num_rows="dynamic", key="j_editor")
        _je1, _je2 = st.columns(2)
        if _je1.button("💾 Save Changes", use_container_width=True, key="j_save2"):
            xp.save_journal(_edited); st.success("Journal updated."); st.rerun()
        _je2.download_button("⬇️ Download Journal CSV",
            _j.to_csv(index=False).encode(), "xerces_journal.csv", "text/csv",
            use_container_width=True)

        if not _closed.empty:
            _cc = _closed.copy()
            _cc["Date"] = pd.to_datetime(_cc["Date"], errors="coerce")
            _cc = _cc.sort_values("Date")
            _cc["CumPnL"] = _cc["P&L (₹)"].astype(float).cumsum()
            fig_j = go.Figure(go.Scatter(x=_cc["Date"], y=_cc["CumPnL"],
                mode="lines+markers",
                line=dict(color="#00e87a", width=2),
                marker=dict(size=7, color="#00c8ff"),
                fill="tozeroy", fillcolor="rgba(0,232,122,0.08)"))
            fig_j.update_layout(
                height=280, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#ddeeff", family="Space Mono", size=10),
                title=dict(text="Cumulative P&L Curve", font=dict(color="#00c8ff", size=12)),
                xaxis=dict(gridcolor="rgba(0,200,255,0.04)"),
                yaxis=dict(gridcolor="rgba(0,200,255,0.04)", tickprefix="₹"),
                margin=dict(l=10, r=10, t=40, b=10),
            )
            st.plotly_chart(fig_j, use_container_width=True)
    else:
        st.info("No trades logged yet. Add your first entry above.")
