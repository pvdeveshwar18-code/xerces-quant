import streamlit as st
import pandas as pd
import numpy as np
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from analytics.ml_classifier import train_and_predict_ml_signal

def render_chart_tab(
    df: pd.DataFrame, 
    signal: str, 
    strength: int, 
    rsi_val: float, 
    macd_v: float, 
    macd_sv: float, 
    atr_val: float, 
    sl_price: float, 
    tp_price: float, 
    close: float, 
    vol20: float, 
    last: pd.Series, 
    show_sma: bool, 
    show_bb: bool, 
    show_vol: bool,
    buy_x: list, 
    buy_y: list, 
    sell_x: list, 
    sell_y: list, 
    str_clr: str
):
    """Render main stock chart, technical indicator plots, and Machine Learning directional classifier."""
    rows = 4 if show_vol else 3
    row_h = ([0.48, 0.18, 0.18, 0.16] if show_vol else [0.56, 0.22, 0.22])
    titles = ["Price + Indicators", "RSI (14)", "MACD"] + (["Volume"] if show_vol else [])
    
    fig = make_subplots(rows=rows, cols=1, shared_xaxes=True, row_heights=row_h,
                        vertical_spacing=0.025, subplot_titles=titles,
                        specs=[[{"secondary_y": False}]] * rows)

    fig.add_trace(go.Candlestick(
        x=df["Date"], open=df["Open"], high=df["High"], low=df["Low"], close=df["Close"],
        name="OHLC", increasing_line_color="#00e87a", decreasing_line_color="#ff3355",
        increasing_fillcolor="rgba(0,232,122,0.25)", decreasing_fillcolor="rgba(255,51,85,0.25)"
    ), row=1, col=1)

    if show_sma:
        for col_n, clr, dsh in [("SMA_20", "#00c8ff", "dot"), ("SMA_50", "#ffcc00", "dash"), ("SMA_200", "#ff6b35", "solid")]:
            if col_n in df.columns:
                fig.add_trace(go.Scatter(x=df["Date"], y=df[col_n], name=col_n.replace("_", " "),
                    line=dict(color=clr, width=1.2, dash=dsh), opacity=0.85), row=1, col=1)

    if show_bb and "BB_Upper" in df.columns:
        fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_Upper"], name="BB Upper",
            line=dict(color="rgba(124,78,255,0.5)", width=1, dash="dot")), row=1, col=1)
        fig.add_trace(go.Scatter(x=df["Date"], y=df["BB_Lower"], name="BB Lower",
            line=dict(color="rgba(124,78,255,0.5)", width=1, dash="dot"),
            fill="tonexty", fillcolor="rgba(124,78,255,0.04)"), row=1, col=1)

    fig.add_hline(y=sl_price, line_dash="dash", line_color="rgba(255,51,85,0.6)",
                  annotation_text=f"SL ₹{sl_price:,.0f}", row=1, col=1)
    fig.add_hline(y=tp_price, line_dash="dash", line_color="rgba(0,232,122,0.6)",
                  annotation_text=f"TP ₹{tp_price:,.0f}", row=1, col=1)

    if buy_x:
        fig.add_trace(go.Scatter(x=buy_x, y=buy_y, mode="markers", name="Buy Entry",
            marker=dict(symbol="triangle-up", size=9, color="#00e87a",
                        line=dict(width=1, color="#020813"))), row=1, col=1)
    if sell_x:
        fig.add_trace(go.Scatter(x=sell_x, y=sell_y, mode="markers", name="Sell Exit",
            marker=dict(symbol="triangle-down", size=9, color="#ff3355",
                        line=dict(width=1, color="#020813"))), row=1, col=1)

    fig.add_trace(go.Scatter(x=df["Date"], y=df["RSI_14"], name="RSI 14",
        line=dict(color="#00c8ff", width=1.5)), row=2, col=1)
    for lvl, lc in [(70, "rgba(255,51,85,0.4)"), (30, "rgba(0,232,122,0.4)"), (50, "rgba(255,255,255,0.08)")]:
        fig.add_hline(y=lvl, line_dash="dot", line_color=lc, row=2, col=1)

    mc_colors = ["#00e87a" if v >= 0 else "#ff3355" for v in df["MACD_Hist"].fillna(0)]
    fig.add_trace(go.Bar(x=df["Date"], y=df["MACD_Hist"], name="MACD Hist", marker_color=mc_colors, opacity=0.7), row=3, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD"], name="MACD", line=dict(color="#00c8ff", width=1.2)), row=3, col=1)
    fig.add_trace(go.Scatter(x=df["Date"], y=df["MACD_Signal"], name="Signal", line=dict(color="#ffcc00", width=1.2, dash="dot")), row=3, col=1)
    fig.add_hline(y=0, line_dash="dot", line_color="rgba(255,255,255,0.1)", row=3, col=1)

    if show_vol and "Volume" in df.columns:
        vc = ["rgba(0,232,122,0.4)" if r["Close"] >= r["Open"] else "rgba(255,51,85,0.4)" for _, r in df.iterrows()]
        fig.add_trace(go.Bar(x=df["Date"], y=df["Volume"], name="Volume", marker_color=vc), row=4, col=1)

    fig.update_layout(
        height=780, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ddeeff", family="Space Mono", size=10),
        xaxis_rangeslider_visible=False, showlegend=True,
        legend=dict(bgcolor="rgba(7,18,32,0.5)", bordercolor="rgba(0,200,255,0.15)", borderwidth=1, font=dict(size=9)),
        margin=dict(l=10, r=10, t=30, b=10),
    )
    for i in range(1, rows + 1):
        fig.update_xaxes(gridcolor="rgba(0,200,255,0.04)", row=i, col=1)
        fig.update_yaxes(gridcolor="rgba(0,200,255,0.04)", row=i, col=1)
    fig.update_xaxes(rangeselector=dict(
        buttons=[dict(count=1, label="1M", step="month"), dict(count=3, label="3M", step="month"),
                 dict(count=6, label="6M", step="month"), dict(count=1, label="1Y", step="year"),
                 dict(count=2, label="2Y", step="year"), dict(step="all", label="5Y")],
        bgcolor="rgba(7,18,32,0.7)", activecolor="#00c8ff", font=dict(color="#ddeeff", size=9)
    ), row=1, col=1)
    
    st.plotly_chart(fig, use_container_width=True)

    # Calculate Machine Learning Classifier Prediction
    ml_res = train_and_predict_ml_signal(df)

    c1, c2, c3 = st.columns([1, 1, 1.5])
    with c1:
        sig_color = "buy" if signal == "BUY" else "sell" if signal == "SELL" else "hold"
        st.markdown(f"""<div class="glass-card" style="text-align:center;">
            <p class="glass-label">Technical Rule Signal</p>
            <div class="signal-{sig_color}">{signal}</div>
            <div style="background:rgba(255,255,255,0.05);border-radius:4px;height:6px;margin:8px 0;">
              <div style="width:{strength}%;height:6px;border-radius:4px;background:{str_clr};"></div>
            </div>
            <p style="font-size:10px;color:#6a90aa;margin:0;">Strength {strength}/100</p>
        </div>""", unsafe_allow_html=True)

    with c2:
        ml_sig = ml_res["ml_signal"]
        ml_clr = "#00e87a" if ml_sig == "BUY" else "#ff3355" if ml_sig == "SELL" else "#ffcc00"
        st.markdown(f"""<div class="glass-card" style="text-align:center;">
            <p class="glass-label">🤖 ML Random Forest Signal</p>
            <div class="signal-{'buy' if ml_sig=='BUY' else 'sell' if ml_sig=='SELL' else 'hold'}">{ml_sig}</div>
            <div style="font-size:11px;font-family:'Space Mono',monospace;margin-top:6px;color:#ddeeff;">
                Bull: <span style="color:#00e87a;">{ml_res['prob_bull']}%</span> | 
                Bear: <span style="color:#ff3355;">{ml_res['prob_bear']}%</span>
            </div>
            <p style="font-size:10px;color:#6a90aa;margin-top:2px;">Model Confidence {ml_res['confidence']}%</p>
        </div>""", unsafe_allow_html=True)
        
    with c3:
        bb_pct = ""
        if pd.notna(last.get("BB_Upper")) and pd.notna(last.get("BB_Lower")):
            bbrng = float(last["BB_Upper"]) - float(last["BB_Lower"])
            bb_pct = f"{(close - float(last['BB_Lower'])) / bbrng * 100:.0f}%" if bbrng > 0 else "—"
        sk = float(last.get("Stoch_K", 50) or 50)
        st.markdown(f"""<div class="glass-card">
            <p class="glass-label">Core Indicator Readings</p>
            <div style="display:grid;grid-template-columns:1fr 1fr 1fr;gap:6px;margin-top:6px;font-size:11px;font-family:'Space Mono',monospace;">
                <div>RSI: <span style="color:{'#ff3355' if rsi_val > 70 else '#00e87a' if rsi_val < 30 else '#00c8ff'}">{rsi_val:.1f}</span></div>
                <div>MACD: <span style="color:{'#00e87a' if macd_v > macd_sv else '#ff3355'}">{macd_v:.2f}</span></div>
                <div>ATR(14): <span style="color:#ffcc00;">₹{atr_val:.2f}</span></div>
                <div>Stoch %K: <span style="color:{'#ff3355' if sk > 80 else '#00e87a' if sk < 20 else '#ddeeff'}">{sk:.0f}</span></div>
                <div>BB Pos: <span style="color:#7c4dff;">{bb_pct}</span></div>
                <div>Volatility: <span style="color:#ddeeff;">{vol20:.1%}</span></div>
                <div>SMA 200: <span style="color:#ff6b35;">₹{float(last.get('SMA_200', 0) or 0):,.0f}</span></div>
                <div>SMA 50: <span style="color:#ffcc00;">₹{float(last.get('SMA_50', 0) or 0):,.0f}</span></div>
                <div>SMA 20: <span style="color:#00c8ff;">₹{float(last.get('SMA_20', 0) or 0):,.0f}</span></div>
            </div>
        </div>""", unsafe_allow_html=True)
