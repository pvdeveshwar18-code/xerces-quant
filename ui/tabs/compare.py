import streamlit as st
import plotly.graph_objects as go
import xerces_plus as xp

def render_compare_tab(ALL_STOCKS: dict):
    """Render Stock Comparison & Correlation tab."""
    st.markdown('<p class="section-header">[ 🔄 COMPARE 2–4 STOCKS SIDE-BY-SIDE ]</p>', unsafe_allow_html=True)
    _cmp_defaults = [k for k in ALL_STOCKS if any(x in k for x in
                     ["Reliance (", "TCS (", "HDFC Bank ("])][:3]
    _cmp_keys = st.multiselect("Select 2 to 4 stocks", list(ALL_STOCKS.keys()),
                                default=_cmp_defaults, max_selections=4, key="cmp_sel")
    _cmp_period = st.select_slider("Period", ["3mo","6mo","1y","2y","5y"], value="1y", key="cmp_period")

    if len(_cmp_keys) >= 2:
        _tickers = [ALL_STOCKS[k] for k in _cmp_keys]
        _labels  = [k.split(" (")[0] for k in _cmp_keys]
        with st.spinner("Fetching and computing..."):
            _nrm, _corr, _stats = xp.compare_stocks(_tickers, period=_cmp_period)
        if _nrm is not None:
            _stats.index = _labels[:len(_stats)]
            _colors = ["#00c8ff","#00e87a","#ffcc00","#ff6b35"]
            fig_c = go.Figure()
            for i, t in enumerate(_nrm.columns):
                lbl = _labels[_tickers.index(t)] if t in _tickers else t
                fig_c.add_trace(go.Scatter(x=_nrm.index, y=_nrm[t], name=lbl,
                                            line=dict(color=_colors[i%4], width=2)))
            fig_c.update_layout(
                height=380, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                font=dict(color="#ddeeff", family="Space Mono", size=10),
                title=dict(text=f"Normalized Price (base=100) — {_cmp_period}", font=dict(color="#00c8ff",size=12)),
                xaxis=dict(gridcolor="rgba(0,200,255,0.04)"),
                yaxis=dict(gridcolor="rgba(0,200,255,0.04)"),
                margin=dict(l=10,r=10,t=40,b=10),
                legend=dict(bgcolor="rgba(7,18,32,0.5)", bordercolor="rgba(0,200,255,0.15)", borderwidth=1)
            )
            st.plotly_chart(fig_c, use_container_width=True)

            cc1, cc2 = st.columns([1.2, 1])
            with cc1:
                st.markdown('<p class="section-header">[ CORRELATION MATRIX (daily returns) ]</p>', unsafe_allow_html=True)
                _corr_disp = _corr.copy()
                _corr_disp.columns = [_labels[_tickers.index(c)] if c in _tickers else c for c in _corr_disp.columns]
                _corr_disp.index   = _corr_disp.columns
                fig_hm = go.Figure(go.Heatmap(
                    z=_corr_disp.values, x=_corr_disp.columns, y=_corr_disp.index,
                    colorscale=[[0,"#ff3355"],[0.5,"#0a192f"],[1,"#00e87a"]],
                    zmin=-1, zmax=1, text=_corr_disp.round(2).values,
                    texttemplate="%{text}", textfont=dict(color="#ddeeff",size=11),
                    colorbar=dict(thickness=10, tickfont=dict(color="#ddeeff",size=9))
                ))
                fig_hm.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#ddeeff",family="Space Mono",size=10),
                    margin=dict(l=10,r=10,t=10,b=10))
                st.plotly_chart(fig_hm, use_container_width=True)
            with cc2:
                st.markdown('<p class="section-header">[ PERFORMANCE STATS ]</p>', unsafe_allow_html=True)
                st.dataframe(_stats, use_container_width=True)
        else:
            st.warning("Could not fetch comparison data.")
    else:
        st.info("Select at least 2 stocks to compare.")
