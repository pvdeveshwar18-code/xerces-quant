import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from statsmodels.tsa.stattools import adfuller

def render_forecast_tab(
    df: pd.DataFrame, 
    selected_name: str, 
    selected_ticker: str, 
    history_period: str, 
    close: float, 
    cached_forecast_bundle_func
):
    """Render Multi-Horizon Price Forecast tab with ARIMA + Holt-Winters + Naive Ensemble."""
    st.markdown(f'<p class="section-header">[ 🔮 MULTI-HORIZON PRICE FORECAST — {selected_name} ]</p>', unsafe_allow_html=True)
    
    hz_col1, hz_col2 = st.columns(2)
    with hz_col1:
        horizon_type = st.radio(
            "Forecast Horizon Type", 
            ["Swing Trade (Days)", "Long-Term Hold (Years)"], 
            index=0 if st.session_state.get("fc_horizon_type", "Swing Trade (Days)") == "Swing Trade (Days)" else 1,
            key="horizon_type_selector"
        )
    with hz_col2:
        if horizon_type == "Swing Trade (Days)":
            steps_input = st.slider(
                "Forecast Steps (Trading Days)", 
                min_value=1, max_value=252, 
                value=st.session_state.get("fc_steps", 60), step=1,
                key="steps_slider"
            )
            if (st.session_state.get("fc_horizon_type") != "Swing Trade (Days)" or 
                st.session_state.get("fc_steps") != steps_input):
                st.session_state["fc_horizon_type"] = "Swing Trade (Days)"
                st.session_state["fc_steps"] = steps_input
                st.session_state["fc_history_period"] = "2y"
                st.rerun()
            steps = steps_input
        else:
            years_input = st.slider(
                "Forecast Horizon (Years)", 
                min_value=1, max_value=25, 
                value=st.session_state.get("fc_years", 2), step=1,
                key="years_slider"
            )
            if (st.session_state.get("fc_horizon_type") != "Long-Term Hold (Years)" or 
                st.session_state.get("fc_years") != years_input):
                st.session_state["fc_horizon_type"] = "Long-Term Hold (Years)"
                st.session_state["fc_years"] = years_input
                st.session_state["fc_history_period"] = "10y" if years_input <= 5 else "max"
                st.rerun()
            steps = years_input * 252

    price_series = df["Close"].astype(float).dropna()
    last_date    = pd.to_datetime(df["Date"].iloc[-1])
    fc_dates     = pd.bdate_range(start=last_date + pd.Timedelta(days=1), periods=steps)
    target_end   = fc_dates[-1]

    if steps <= 0:
        st.warning("Data already extends past target horizon.")
    else:
        with st.spinner(f"Fitting ARIMA + Holt-Winters + naive ensemble for {steps} steps..."):
            try:
                bundle = cached_forecast_bundle_func(
                    selected_ticker, history_period, steps, holdout=60
                )
                if bundle is None:
                    raise ValueError("Insufficient price history for forecasting")

                fc_mean = bundle["fc_arima"]
                fc_lo = bundle["fc_lo"]
                fc_hi = bundle["fc_hi"]
                fc_series = pd.Series(fc_mean.values, index=fc_dates)
                ci_lo = pd.Series(fc_lo.values, index=fc_dates)
                ci_hi = pd.Series(fc_hi.values, index=fc_dates)
                hw_series = pd.Series(bundle["fc_hw"].values, index=fc_dates)
                naive_series = pd.Series(bundle["fc_naive"].values, index=fc_dates)
                ensemble_series = pd.Series(bundle["fc_ensemble"].values, index=fc_dates)

                arima_order = bundle["arima_order"]
                aic_val = bundle["aic"]
                target_arima = bundle["target_arima"]
                target_hw = bundle["target_hw"]
                consensus = bundle["target_ensemble"]
                upside_a = (target_arima - close) / close * 100
                upside_hw = (target_hw - close) / close * 100
                upside_c = (consensus - close) / close * 100
                mape = bundle.get("arima_mape")
                dir_acc = bundle.get("dir_acc")
                hw_mape = bundle.get("hw_mape")
                naive_mape = bundle.get("naive_mape")
                edge = bundle.get("edge_vs_naive")
                weights = bundle.get("weights", {})
                best_model = bundle.get("best_model", "naive")

                fa1, fa2, fa3, fa4, fa5 = st.columns(5)
                for col, lbl, val, clr in zip([fa1, fa2, fa3, fa4, fa5],
                    ["Current Price", "Weighted Ensemble", "ARIMA Target", "Holt-Winters Target", "Best Model (holdout)"],
                    [f"₹{close:,.2f}",
                     f"₹{consensus:,.0f} ({'▲' if upside_c>=0 else '▼'}{abs(upside_c):.1f}%)",
                     f"₹{target_arima:,.0f} ({'▲' if upside_a>=0 else '▼'}{abs(upside_a):.1f}%)",
                     f"₹{target_hw:,.0f} ({'▲' if upside_hw>=0 else '▼'}{abs(upside_hw):.1f}%)",
                     f"{best_model.upper()} ({weights.get(best_model, 0)*100:.0f}% wt)"],
                    ["#ddeeff", "#00e87a", "#fbbf24", "#00c8ff", "#ff6b35"]):
                    col.markdown(f'<div class="glass-card"><p class="glass-label">{lbl}</p>'
                                 f'<div class="glass-value" style="color:{clr};font-size:0.95rem;">{val}</div></div>',
                                 unsafe_allow_html=True)

                if mape is not None:
                    am1, am2, am3, am4, am5 = st.columns(5)
                    mape_clr = "#00e87a" if mape < 5 else "#ffcc00" if mape < 10 else "#ff3355"
                    dacc_clr = "#00e87a" if (dir_acc or 0) > 60 else "#ffcc00" if (dir_acc or 0) > 50 else "#ff3355"
                    hw_clr = "#00e87a" if (hw_mape or 99) < 5 else "#ffcc00" if (hw_mape or 99) < 10 else "#ff3355"
                    nv_clr = "#00e87a" if (naive_mape or 99) < 5 else "#ffcc00" if (naive_mape or 99) < 10 else "#ff3355"
                    edge_clr = "#00e87a" if (edge or 0) > 0 else "#ff3355"
                    am1.markdown(f'<div class="glass-card"><p class="glass-label">ARIMA MAPE (60d)</p>'
                                 f'<div class="glass-value" style="color:{mape_clr};">{mape:.2f}%</div></div>',
                                 unsafe_allow_html=True)
                    am2.markdown(f'<div class="glass-card"><p class="glass-label">Holt-Winters MAPE</p>'
                                 f'<div class="glass-value" style="color:{hw_clr};">{hw_mape:.2f}%</div></div>' if hw_mape else
                                 '<div class="glass-card"><p class="glass-label">Holt-Winters MAPE</p><div class="glass-value">N/A</div></div>',
                                 unsafe_allow_html=True)
                    am3.markdown(f'<div class="glass-card"><p class="glass-label">Naive Baseline MAPE</p>'
                                 f'<div class="glass-value" style="color:{nv_clr};">{naive_mape:.2f}%</div></div>' if naive_mape else
                                 '<div class="glass-card"><p class="glass-label">Naive Baseline MAPE</p><div class="glass-value">N/A</div></div>',
                                 unsafe_allow_html=True)
                    am4.markdown(f'<div class="glass-card"><p class="glass-label">Directional Accuracy</p>'
                                 f'<div class="glass-value" style="color:{dacc_clr};">{dir_acc:.0f}%</div></div>',
                                 unsafe_allow_html=True)
                    am5.markdown(f'<div class="glass-card"><p class="glass-label">Edge vs Naive</p>'
                                 f'<div class="glass-value" style="color:{edge_clr};">{edge:+.1f}%</div>'
                                 f'<p style="font-size:10px;color:#6a90aa;margin:3px 0 0;">Positive = ensemble beats drift</p></div>',
                                 unsafe_allow_html=True)

                fig2 = go.Figure()
                hp   = price_series.iloc[-504:]
                hd   = pd.to_datetime(df["Date"].iloc[-504:])
                fig2.add_trace(go.Scatter(x=hd, y=hp.values, name="Historical Data", line=dict(color="#7c6ef8",width=1.8)))
                fig2.add_trace(go.Scatter(x=fc_series.index, y=fc_series.values, name="ARIMA", line=dict(color="#f97316",width=2,dash="dash")))
                fig2.add_trace(go.Scatter(x=hw_series.index, y=hw_series.values, name="Holt-Winters", line=dict(color="#00c8ff",width=1.5,dash="dashdot")))
                fig2.add_trace(go.Scatter(x=naive_series.index, y=naive_series.values, name="Naive Baseline", line=dict(color="#94a3b8",width=1,dash="dot")))
                fig2.add_trace(go.Scatter(x=ensemble_series.index, y=ensemble_series.values, name="Weighted Ensemble",
                    line=dict(color="#00e87a",width=2,dash="longdash")))
                fig2.add_trace(go.Scatter(
                    x=list(ci_hi.index)+list(ci_lo.index[::-1]),
                    y=list(ci_hi.values)+list(ci_lo.values[::-1]),
                    fill="toself", fillcolor="rgba(249,115,22,0.08)",
                    line=dict(color="rgba(0,0,0,0)"), name="ARIMA 90% CI"))
                fig2.add_vline(x=str(last_date), line_dash="dot", line_color="rgba(100,100,100,0.4)")
                fig2.add_annotation(x=str(target_end), y=consensus,
                    text=f"Consensus Target<br>{target_end.strftime('%d %b %Y')}<br>₹{consensus:,.0f}",
                    showarrow=True, arrowhead=2, arrowcolor="#00e87a",
                    font=dict(color="#00e87a",size=10), bgcolor="rgba(7,18,32,0.85)",
                    bordercolor="#00e87a", borderwidth=1)
                fig2.update_layout(height=440, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                    font=dict(color="#ddeeff",family="Space Mono",size=10),
                    legend=dict(bgcolor="rgba(7,18,32,0.5)",bordercolor="rgba(0,200,255,0.2)",borderwidth=1),
                    margin=dict(l=10,r=10,t=20,b=10),
                    xaxis=dict(gridcolor="rgba(0,200,255,0.04)"),
                    yaxis=dict(gridcolor="rgba(0,200,255,0.04)",tickprefix="₹"))
                st.plotly_chart(fig2, use_container_width=True)

                fc_df2 = pd.DataFrame({"Ensemble": ensemble_series, "Forecast": fc_series, "HW": hw_series, "Naive": naive_series, "CI_Lo": ci_lo, "CI_Hi": ci_hi})
                
                if horizon_type == "Long-Term Hold (Years)" and st.session_state.get("fc_years", 2) > 2:
                    st.markdown('<p class="section-header">[ 📅 YEAR-BY-YEAR ARIMA PRICE TARGETS ]</p>', unsafe_allow_html=True)
                    fc_df2["Year"] = fc_df2.index.to_period("A")
                    yearly = fc_df2.groupby("Year").agg(
                        Ensemble=("Ensemble","last"), Forecast=("Forecast","last"), HW=("HW","last"),
                        CI_Lo=("CI_Lo","last"), CI_Hi=("CI_Hi","last")
                    ).reset_index()
                    yearly["Year_str"] = yearly["Year"].dt.strftime("Year %Y")
                    yearly["YoY_pct"]   = yearly["Ensemble"].pct_change() * 100
                    yearly.loc[0,"YoY_pct"] = (yearly.loc[0,"Ensemble"] - close) / close * 100

                    for i in range(0, len(yearly), 6):
                        chunk = yearly.iloc[i:i+6]
                        cols  = st.columns(len(chunk))
                        for col, (_,row) in zip(cols, chunk.iterrows()):
                            chg   = row["YoY_pct"]
                            arrow = "▲" if chg>=0 else "▼"
                            clr   = "#00e87a" if chg>=0 else "#ff3355"
                            col.markdown(f"""
<div style="background:rgba(7,18,32,0.65);border:1px solid rgba(0,200,255,0.15);border-radius:6px;
     padding:9px 7px;text-align:center;margin-bottom:6px;">
  <div style="font-size:9px;font-family:'Space Mono',monospace;color:#6a90aa;text-transform:uppercase;">{row['Year_str']}</div>
  <div style="font-family:'Orbitron',sans-serif;font-size:.95rem;font-weight:700;color:#fbbf24;margin:3px 0;">₹{row['Ensemble']:,.0f}</div>
  <div style="font-size:9px;color:{clr};font-weight:600;">{arrow} {abs(chg):.1f}%</div>
  <div style="font-size:8px;color:rgba(100,120,140,0.8);margin-top:2px;">HW: ₹{row['HW']:,.0f}</div>
  <div style="font-size:8px;color:rgba(100,120,140,0.5);">₹{row['CI_Lo']:,.0f}–₹{row['CI_Hi']:,.0f}</div>
</div>""", unsafe_allow_html=True)
                else:
                    st.markdown('<p class="section-header">[ 📅 MONTH-BY-MONTH ARIMA PRICE TARGETS ]</p>', unsafe_allow_html=True)
                    fc_df2["Month"] = fc_df2.index.to_period("M")
                    monthly = fc_df2.groupby("Month").agg(
                        Ensemble=("Ensemble","last"), Forecast=("Forecast","last"), HW=("HW","last"),
                        CI_Lo=("CI_Lo","last"), CI_Hi=("CI_Hi","last")
                    ).reset_index()
                    monthly["Month_str"] = monthly["Month"].dt.strftime("%b %Y")
                    monthly["MoM_pct"]   = monthly["Ensemble"].pct_change() * 100
                    monthly.loc[0,"MoM_pct"] = (monthly.loc[0,"Ensemble"] - close) / close * 100

                    for i in range(0, len(monthly), 6):
                        chunk = monthly.iloc[i:i+6]
                        cols  = st.columns(len(chunk))
                        for col, (_,row) in zip(cols, chunk.iterrows()):
                            chg   = row["MoM_pct"]
                            arrow = "▲" if chg>=0 else "▼"
                            clr   = "#00e87a" if chg>=0 else "#ff3355"
                            col.markdown(f"""
<div style="background:rgba(7,18,32,0.65);border:1px solid rgba(0,200,255,0.15);border-radius:6px;
     padding:9px 7px;text-align:center;margin-bottom:6px;">
  <div style="font-size:9px;font-family:'Space Mono',monospace;color:#6a90aa;text-transform:uppercase;">{row['Month_str']}</div>
  <div style="font-family:'Orbitron',sans-serif;font-size:.95rem;font-weight:700;color:#fbbf24;margin:3px 0;">₹{row['Ensemble']:,.0f}</div>
  <div style="font-size:9px;color:{clr};font-weight:600;">{arrow} {abs(chg):.1f}%</div>
  <div style="font-size:8px;color:rgba(100,120,140,0.8);margin-top:2px;">HW: ₹{row['HW']:,.0f}</div>
  <div style="font-size:8px;color:rgba(100,120,140,0.5);">₹{row['CI_Lo']:,.0f}–₹{row['CI_Hi']:,.0f}</div>
</div>""", unsafe_allow_html=True)

                tbl = fc_df2.round(2)
                st.download_button("⬇️ Download Forecast CSV",
                                   tbl.to_csv().encode(),
                                   f"{selected_name}_forecast.csv","text/csv")

                with st.expander("🔬 Model diagnostics"):
                    pv = adfuller(np.log(price_series.dropna()))[1]
                    st.markdown(f"""
| Parameter | Value |
|---|---|
| Ticker | {selected_ticker} |
| ARIMA order | {arima_order} |
| AIC | {aic_val} |
| MAPE (60-day holdout) | {f"{mape:.2f}%" if mape is not None else "N/A"} |
| Directional accuracy | {f"{dir_acc:.1f}%" if dir_acc is not None else "N/A"} |
| Ensemble weights | ARIMA {weights.get('arima',0)*100:.0f}% · HW {weights.get('hw',0)*100:.0f}% · Naive {weights.get('naive',0)*100:.0f}% |
| Edge vs naive | {f"{edge:+.1f}%" if edge is not None else "N/A"} |
| Training observations | {len(price_series):,} |
| Forecast horizon | {steps} trading days |
| Data range | {str(df["Date"].iloc[0])[:10]} to {str(df["Date"].iloc[-1])[:10]} |
""")
            except Exception as e:
                st.error(f"Forecast error: {e}")
