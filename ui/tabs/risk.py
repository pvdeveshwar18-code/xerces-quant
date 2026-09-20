import streamlit as st
import pandas as pd
from analytics.risk_models import compute_cvar, run_historical_stress_test

def render_risk_tab(df: pd.DataFrame, selected_name: str, selected_ticker: str, close: float, sl_price: float, tp_price: float, allocated_capital: float, risk_per_trade: float):
    """Render Position Sizing, CVaR Expected Shortfall, and Historical Stress Testing tab."""
    st.markdown(f'<p class="section-header">[ RISK CALCULATOR & CVaR STRESS TEST — {selected_name} ]</p>', unsafe_allow_html=True)
    
    # Section 1: Position Sizing
    r1, r2 = st.columns(2)
    with r1:
        entry_px  = st.number_input("Entry Price", value=round(close, 2), step=1.0)
        stop_px   = st.number_input("Stop Loss",   value=round(sl_price, 2), step=1.0)
        target_px = st.number_input("Take Profit", value=round(tp_price, 2), step=1.0)
    with r2:
        cap2      = st.number_input("Capital", value=float(allocated_capital), step=1000.0)
        risk_pct2 = st.slider("Risk %", 0.5, 10.0, float(risk_per_trade), step=0.5)
        n_trades  = st.number_input("Simultaneous Trades", min_value=1, max_value=20, value=5)

    if entry_px > 0 and entry_px > stop_px > 0:
        rps   = entry_px - stop_px
        rws   = target_px - entry_px
        rr    = rws / rps if rps > 0 else 0
        car   = cap2 * (risk_pct2 / 100)
        qty_c = max(1, int(car / rps))
        tv    = qty_c * entry_px
        ml    = qty_c * rps
        mg    = qty_c * rws

        rc1, rc2, rc3, rc4 = st.columns(4)
        for col, lbl, val, clr in zip(
            [rc1, rc2, rc3, rc4],
            ["Qty to Buy", "Total Value", "Max Loss", "Max Gain"],
            [str(qty_c), f"₹{tv:,.0f}", f"₹{ml:,.0f}", f"₹{mg:,.0f}"],
            ["#00c8ff", "#ddeeff", "#ff3355", "#00e87a"]
        ):
            col.markdown(
                f'<div class="glass-card"><p class="glass-label">{lbl}</p>'
                f'<div class="glass-value" style="color:{clr};font-size:1rem;">{val}</div></div>',
                unsafe_allow_html=True
            )
        rr_clr = "#00e87a" if rr >= 2 else "#ffcc00" if rr >= 1 else "#ff3355"
        st.markdown(
            f'<div class="glass-card" style="text-align:center;"><p class="glass-label">Risk:Reward</p>'
            f'<div class="glass-value" style="color:{rr_clr};">1 : {rr:.2f}</div>'
            f'<p style="font-size:10px;color:#6a90aa;margin:3px 0 0;">Portfolio risk at {n_trades} trades: ₹{ml * n_trades:,.0f}</p></div>',
            unsafe_allow_html=True
        )
    else:
        st.warning("Stop loss must be below entry price.")

    st.markdown("<br>", unsafe_allow_html=True)

    # Section 2: Conditional Value-at-Risk (CVaR / Expected Shortfall)
    st.markdown('<p class="section-header">[ 📉 CONDITIONAL VALUE-AT-RISK (CVaR / EXPECTED SHORTFALL) ]</p>', unsafe_allow_html=True)
    cvar_res = compute_cvar(df, confidence_level=0.95, portfolio_value=allocated_capital)

    cv1, cv2, cv3, cv4 = st.columns(4)
    cv1.markdown(f'<div class="glass-card"><p class="glass-label">VaR (95% 1-Day)</p><div class="glass-value" style="color:#ffcc00;">{cvar_res["var_95_pct"]}%</div><p style="font-size:10px;color:#6a90aa;margin-top:2px;">₹{cvar_res["var_95_inr"]:,.0f} risk</p></div>', unsafe_allow_html=True)
    cv2.markdown(f'<div class="glass-card"><p class="glass-label">CVaR / Expected Shortfall (95%)</p><div class="glass-value" style="color:#ff3355;">{cvar_res["cvar_95_pct"]}%</div><p style="font-size:10px;color:#6a90aa;margin-top:2px;">₹{cvar_res["cvar_95_inr"]:,.0f} tail loss</p></div>', unsafe_allow_html=True)
    cv3.markdown(f'<div class="glass-card"><p class="glass-label">VaR (99% 1-Day)</p><div class="glass-value" style="color:#ffcc00;">{cvar_res["var_99_pct"]}%</div><p style="font-size:10px;color:#6a90aa;margin-top:2px;">₹{cvar_res["var_99_inr"]:,.0f} risk</p></div>', unsafe_allow_html=True)
    cv4.markdown(f'<div class="glass-card"><p class="glass-label">CVaR / Expected Shortfall (99%)</p><div class="glass-value" style="color:#ff3355;">{cvar_res["cvar_99_pct"]}%</div><p style="font-size:10px;color:#6a90aa;margin-top:2px;">₹{cvar_res["cvar_99_inr"]:,.0f} tail loss</p></div>', unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Section 3: Historical Crisis Stress Testing Simulator
    st.markdown('<p class="section-header">[ 🌪️ HISTORICAL CRISIS STRESS TEST SIMULATOR ]</p>', unsafe_allow_html=True)
    scenarios = run_historical_stress_test(df, portfolio_value=allocated_capital)

    for sc in scenarios:
        st.markdown(f"""
<div class="glass-card" style="border-left: 4px solid {sc['color']}; padding: 10px 14px; margin-bottom: 8px;">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="font-family:'Orbitron',sans-serif; font-weight:700; color:#ddeeff; font-size:13px;">{sc['scenario']}</span>
        <span style="font-family:'Space Mono',monospace; font-size:11px; font-weight:bold; color:{sc['color']};">{sc['severity']} RISK</span>
    </div>
    <div style="display:grid; grid-template-columns: 1fr 1fr 1fr; gap: 10px; margin-top:8px; font-family:'Space Mono',monospace; font-size:11px;">
        <div>Market Shock: <span style="color:#ffcc00;">{sc['market_shock_pct']}%</span></div>
        <div>Stock Shock Impact: <span style="color:{sc['color']}; font-weight:bold;">{sc['stock_impact_pct']}%</span></div>
        <div>Estimated Portfolio Loss: <span style="color:#ff3355; font-weight:bold;">₹{sc['estimated_loss_inr']:,.2f}</span></div>
    </div>
</div>
""", unsafe_allow_html=True)

    st.markdown("---")
    st.markdown('<p class="section-header">[ ⚡ 1-CLICK INSTANT BROKER ORDER EXECUTION ]</p>', unsafe_allow_html=True)
    st.caption("Route orders instantly to Indian Brokers (Kotak Neo, Zerodha Kite, Upstox, Angel One) or US Brokers (Alpaca).")
    
    col_b1, col_b2, col_b3 = st.columns([1, 1, 1])
    with col_b1:
        selected_broker = st.selectbox("Select Broker API:", ["Kotak Neo (NSE/BSE)", "Zerodha Kite Connect", "Angel One SmartAPI", "Upstox Developer API", "Alpaca US Trading"], key="brk_sel_risk")
    with col_b2:
        order_side = st.selectbox("Action:", ["BUY", "SELL"], key="ord_side_risk")
    with col_b3:
        exec_qty = st.number_input("Order Quantity:", min_value=1, value=max(1, qty_c if 'qty_c' in locals() else 10), step=1, key="exec_qty_risk")

    if st.button("🚀 EXECUTE 1-CLICK ORDER", use_container_width=True, key="exec_order_btn"):
        with st.spinner(f"Executing {order_side} order via {selected_broker}..."):
            try:
                from brokers.executor import execute_order
                res = execute_order(
                    broker_name=selected_broker,
                    symbol=selected_ticker,
                    transaction_type=order_side,
                    quantity=exec_qty,
                    price=entry_px if 'entry_px' in locals() else close
                )
                st.success(f"✅ {res['message']}")
                st.info(f"Order ID: `{res['order_id']}` | Status: `{res['status']}` | Broker: `{res['broker']}`")
            except Exception as e:
                st.error(f"Execution Error: {e}")
