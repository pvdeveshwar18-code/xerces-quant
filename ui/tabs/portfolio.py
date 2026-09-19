import streamlit as st
import pandas as pd
import numpy as np
import yfinance as yf
import plotly.graph_objects as go
from statsmodels.tsa.arima.model import ARIMA
import forecast_engine as fe
from analytics.indicators import add_indicators, get_signal, get_signal_strength
from data.loader import ALL_STOCKS, SECTORS, resolve_ticker, get_sector_peers
from forecast_engine import run_holt_winters

def render_portfolio_tab(allocated_capital: float):
    """Render Custom Portfolio Tracker & ROTATION ADVISOR tab.
    Includes optional loading of Kotak Neo portfolio via the global credentials.
    """
    # ── SUBSECTION 1: CUSTOM PORTFOLIO TRACKER & ROTATION ADVISOR ────────────
    import streamlit as st
    from utils.portfolio import fetch_kotak_portfolio

    # Button to load Kotak Neo portfolio
    if st.button("Load Kotak Neo Portfolio", key="load_kotak_portfolio"):
        with st.spinner("Fetching your Kotak Neo holdings…"):
            portfolio_data = fetch_kotak_portfolio()
        if portfolio_data:
            df = pd.DataFrame(portfolio_data)
            st.subheader("Kotak Neo Portfolio")
            st.dataframe(df.style.hide_index().background_gradient(subset=["market_value"], cmap="RdYlGn"))
        else:
            st.info("No holdings retrieved or portfolio is empty.")

    # Existing custom portfolio editor follows
    st.markdown('<p class="section-header">[ 💼 MY CUSTOM PORTFOLIO TRACKER & ROTATION ADVISOR ]</p>', unsafe_allow_html=True)
    st.caption("Enter your custom portfolio details below to project 1-year returns and receive rotation optimization advice.")

    if "custom_portfolio" not in st.session_state:
        st.session_state["custom_portfolio"] = pd.DataFrame([
            {"Ticker": "RELIANCE", "Quantity": 10, "Buy Price (₹)": 2400.0},
            {"Ticker": "TCS", "Quantity": 5, "Buy Price (₹)": 3800.0},
            {"Ticker": "HDFCBANK", "Quantity": 15, "Buy Price (₹)": 1500.0}
        ])

    edited_portfolio = st.data_editor(
        st.session_state["custom_portfolio"],
        num_rows="dynamic",
        column_config={
            "Ticker": st.column_config.TextColumn("Stock Symbol", help="e.g. RELIANCE, TCS, SBIN", required=True),
            "Quantity": st.column_config.NumberColumn("Quantity", min_value=1, step=1, required=True),
            "Buy Price (₹)": st.column_config.NumberColumn("Buy Price (₹)", min_value=0.0, step=10.0, required=True)
        },
        use_container_width=True,
        key="portfolio_editor"
    )
    st.session_state["custom_portfolio"] = edited_portfolio

    if not edited_portfolio.empty:
        valid_rows = edited_portfolio.dropna(subset=["Ticker", "Quantity", "Buy Price (₹)"])
        if not valid_rows.empty:
            port_tickers_list = []
            peer_tickers_map = {}
            all_tickers_to_fetch = set()

            for _, row in valid_rows.iterrows():
                sym_resolved = resolve_ticker(str(row["Ticker"]))
                port_tickers_list.append((str(row["Ticker"]), sym_resolved, int(row["Quantity"]), float(row["Buy Price (₹)"])))
                all_tickers_to_fetch.add(sym_resolved)

                sector, peers = get_sector_peers(sym_resolved, max_peers=2)
                if sector:
                    peer_tickers_map[sym_resolved] = (sector, peers)
                    for p in peers:
                        all_tickers_to_fetch.add(p)

            with st.spinner("Downloading portfolio and sector peer market data..."):
                try:
                    batch_port_df = yf.download(
                        list(all_tickers_to_fetch), period="2y", interval="1d",
                        auto_adjust=True, progress=False, timeout=25, group_by="ticker"
                    )

                    def get_ticker_df(ticker_sym):
                        if isinstance(batch_port_df.columns, pd.MultiIndex):
                            if ticker_sym in batch_port_df.columns.get_level_values(0):
                                return batch_port_df[ticker_sym].dropna()
                            elif ticker_sym in batch_port_df.columns.get_level_values(1):
                                return batch_port_df.xs(ticker_sym, axis=1, level=1).dropna()
                        else:
                            return batch_port_df.dropna()
                        return None

                    peer_info_db = {}
                    for holding_sym, (sector, peers) in peer_tickers_map.items():
                        if sector not in peer_info_db:
                            peer_info_db[sector] = {}
                        for peer in peers:
                            try:
                                pdf = get_ticker_df(peer)
                                if pdf is not None and len(pdf) >= 50:
                                    current_p = float(pdf["Close"].iloc[-1])
                                    prices_s = pdf["Close"].astype(float)
                                    log_s = np.log(prices_s)
                                    try:
                                        fb = fe.compute_forecast_bundle(prices_s, steps=252, holdout=40)
                                        proj_p = fb["target_ensemble"]
                                    except Exception:
                                        arima_m = ARIMA(log_s, order=(1,1,1)).fit()
                                        fc_arima = np.exp(arima_m.forecast(steps=252).iloc[-1])
                                        fc_hw = run_holt_winters(prices_s, steps=252).iloc[-1]
                                        proj_p = (fc_arima + fc_hw) / 2
                                    proj_ret_pct = (proj_p - current_p) / current_p * 100

                                    pdf_ind = add_indicators(pdf.reset_index())
                                    sig = get_signal(pdf_ind)
                                    stre = get_signal_strength(pdf_ind)

                                    peer_info_db[sector][peer] = {
                                        "_proj_return_pct": proj_ret_pct,
                                        "_tech_sig": sig,
                                        "_strength": stre
                                    }
                            except Exception:
                                continue

                    analyzed_rows = []
                    total_cost_basis = 0.0
                    total_current_value = 0.0
                    total_proj_value_1y = 0.0

                    for label_t, sym_resolved, qty, buy_px in port_tickers_list:
                        try:
                            hdf = get_ticker_df(sym_resolved)
                            if hdf is not None and len(hdf) >= 40:
                                current_p = float(hdf["Close"].iloc[-1])
                                cost = qty * buy_px
                                curr_val = qty * current_p

                                prices_s = hdf["Close"].astype(float)
                                try:
                                    fb = fe.compute_forecast_bundle(prices_s, steps=252, holdout=40)
                                    proj_p = fb["target_ensemble"]
                                except Exception:
                                    log_s = np.log(prices_s)
                                    arima_m = ARIMA(log_s, order=(1,1,1)).fit()
                                    fc_arima = np.exp(arima_m.forecast(steps=252).iloc[-1])
                                    fc_hw = run_holt_winters(prices_s, steps=252).iloc[-1]
                                    proj_p = (fc_arima + fc_hw) / 2
                                proj_val_1y = qty * proj_p

                                pnl_curr = curr_val - cost
                                proj_ret_pct = (proj_p - current_p) / current_p * 100

                                total_cost_basis += cost
                                total_current_value += curr_val
                                total_proj_value_1y += proj_val_1y

                                hdf_ind = add_indicators(hdf.reset_index())
                                sig = get_signal(hdf_ind)
                                stre = get_signal_strength(hdf_ind)

                                sector = None
                                if sym_resolved in peer_tickers_map:
                                    sector = peer_tickers_map[sym_resolved][0]
                                if not sector:
                                    clean = sym_resolved.replace(".NS","").replace(".BO","").upper()
                                    for sec, list_of_stocks in SECTORS.items():
                                        if any(sym == clean for _, sym in list_of_stocks):
                                            sector = sec
                                            break

                                verdict = "⚪ HOLD"
                                advice = "Hold. Ratios and technical readings are stable."
                                v_clr = "#ffcc00"

                                if sig == "SELL" or proj_ret_pct < 5.0 or stre < 40:
                                    verdict = "🔴 ROTATE"
                                    v_clr = "#ff3355"
                                    better_peer = None
                                    best_peer_ret = proj_ret_pct
                                    if sector and sector in peer_info_db:
                                        for peer_sym, p_info in peer_info_db[sector].items():
                                            if peer_sym != sym_resolved and p_info["_proj_return_pct"] > best_peer_ret + 5.0:
                                                better_peer = peer_sym.replace(".NS","").replace(".BO","")
                                                best_peer_ret = p_info["_proj_return_pct"]
                                    
                                    if better_peer:
                                        advice = f"Consider rotating into **{better_peer}** (Sector: {sector}). It has a stronger signal and projected 1Y return of {best_peer_ret:.1f}% (+{best_peer_ret - proj_ret_pct:.1f}% uplift)."
                                    else:
                                        sc_results = st.session_state.get("scan_results")
                                        market_alt = None
                                        if sc_results:
                                            buys = [s for s in sc_results if s["_sig"] == "BUY" and s["_str"] >= 70]
                                            if buys:
                                                buys_sorted = sorted(buys, key=lambda x: x["_str"], reverse=True)
                                                market_alt = buys_sorted[0]["Ticker"]
                                        if market_alt:
                                            advice = f"Projected 1Y return is weak ({proj_ret_pct:.1f}%). Suggest rotating into market leader **{market_alt}** (Strength: {buys_sorted[0]['_str']}/100)."
                                        else:
                                            advice = f"Projected 1Y return is weak ({proj_ret_pct:.1f}%). Reallocate to cash or market leaders."
                                elif sig == "BUY" and stre >= 65:
                                    verdict = "🟢 ACCUMULATE"
                                    v_clr = "#00e87a"
                                    advice = f"Strong buy momentum (Strength: {stre}/100) and projected 1Y return of {proj_ret_pct:.1f}%."
                                else:
                                    verdict = "⚪ HOLD"
                                    v_clr = "#ffcc00"
                                    advice = f"Neutral technicals. Projected 1Y return: {proj_ret_pct:.1f}%."

                                analyzed_rows.append({
                                    "Stock": label_t.upper(),
                                    "Qty": qty,
                                    "Buy Price": f"₹{buy_px:,.2f}",
                                    "Current Price": f"₹{current_p:,.2f}",
                                    "Current Value": f"₹{curr_val:,.2f}",
                                    "P&L": f"₹{pnl_curr:,.2f}",
                                    "Projected 1Y Value": f"₹{proj_val_1y:,.2f}",
                                    "Proj. 1Y %": f"{proj_ret_pct:+.1f}%",
                                    "Advice": verdict,
                                    "_adv_text": advice,
                                    "_color": v_clr,
                                    "_pnl": pnl_curr
                                })
                            else:
                                analyzed_rows.append({
                                    "Stock": label_t.upper(), "Qty": qty, "Buy Price": f"₹{buy_px:,.2f}",
                                    "Current Price": "N/A", "Current Value": "N/A", "P&L": "₹0.00",
                                    "Projected 1Y Value": "N/A", "Proj. 1Y %": "0.0%",
                                    "Advice": "⚪ HOLD", "_adv_text": "Could not retrieve historical data.", "_color": "#ffcc00", "_pnl": 0.0
                                })
                        except Exception as e:
                            st.warning(f"Error analyzing {label_t}: {e}")

                    total_pnl = total_current_value - total_cost_basis
                    total_proj_return_pct = (total_proj_value_1y - total_current_value) / total_current_value * 100 if total_current_value > 0 else 0.0

                    pk1, pk2, pk3, pk4 = st.columns(4)
                    pk1.markdown(f'<div class="glass-card"><p class="glass-label">Total Cost Basis</p><div class="glass-value">₹{total_cost_basis:,.2f}</div></div>', unsafe_allow_html=True)
                    pk2.markdown(f'<div class="glass-card"><p class="glass-label">Current Value</p><div class="glass-value" style="color:#00c8ff;">₹{total_current_value:,.2f}</div></div>', unsafe_allow_html=True)
                    pk3.markdown(f'<div class="glass-card"><p class="glass-label">Total Current P&L</p><div class="glass-value" style="color:{"#00e87a" if total_pnl>=0 else "#ff3355"};">₹{total_pnl:,.2f} ({(total_pnl/total_cost_basis*100) if total_cost_basis>0 else 0:+.2f}%)</div></div>', unsafe_allow_html=True)
                    pk4.markdown(f'<div class="glass-card"><p class="glass-label">Projected 1Y Value</p><div class="glass-value" style="color:#00e87a;">₹{total_proj_value_1y:,.2f} ({total_proj_return_pct:+.1f}%)</div></div>', unsafe_allow_html=True)

                    disp_df = pd.DataFrame(analyzed_rows)
                    st.dataframe(
                        disp_df[["Stock", "Qty", "Buy Price", "Current Price", "Current Value", "P&L", "Projected 1Y Value", "Proj. 1Y %", "Advice"]],
                        use_container_width=True, hide_index=True
                    )

                    st.markdown('<p class="section-header">[ 🛡️ PORTFOLIO ROTATION ADVISORY DETAILS ]</p>', unsafe_allow_html=True)
                    for item in analyzed_rows:
                        st.markdown(f"""
<div class="glass-card" style="border-left: 4px solid {item['_color']}; padding: 10px 14px; margin-bottom: 8px;">
    <div style="display:flex; justify-content:space-between; align-items:center;">
        <span style="font-family:'Orbitron',sans-serif; font-weight:700; color:#ddeeff; font-size:13px;">{item['Stock']}</span>
        <span style="font-family:'Space Mono',monospace; font-size:11px; font-weight:bold; color:{item['_color']};">{item['Advice']}</span>
    </div>
    <div style="font-size:12px; color:#a0aec0; margin-top:5px; line-height:1.5;">
        {item['_adv_text']}
    </div>
</div>
""", unsafe_allow_html=True)

                except Exception as e:
                    st.error(f"Error during portfolio analysis run: {e}")

    st.markdown("<br><hr style='border-color:rgba(0,200,255,0.08);'><br>", unsafe_allow_html=True)

    # ── SUBSECTION 2: MPT PORTFOLIO OPTIMIZER (MONTE CARLO) ──────────────────
    st.markdown('<p class="section-header">[ 💼 MPT PORTFOLIO OPTIMIZER — MONTE CARLO 3000 ]</p>', unsafe_allow_html=True)
    default_keys = [k for k in ALL_STOCKS if any(x in k for x in ["Reliance (", "TCS (", "HDFC Bank (", "Infosys (", "SBI ("])][:5]
    sel_keys = st.multiselect("Select 2-10 assets for optimization", list(ALL_STOCKS.keys()), default=default_keys)

    if len(sel_keys) < 2:
        st.warning("Select at least 2 assets.")
    else:
        opt_tickers = [ALL_STOCKS[k] for k in sel_keys]
        opt_names   = [k.split(" (")[0] for k in sel_keys]

        with st.spinner("Downloading returns + Monte Carlo simulation..."):
            try:
                dp = yf.download(opt_tickers, period="2y", interval="1d", auto_adjust=True, progress=False)
                if dp is not None and not dp.empty:
                    if isinstance(dp.columns, pd.MultiIndex):
                        lvls = dp.columns.get_level_values(0).unique().tolist()
                        if "Close" in lvls:
                            close_df = dp["Close"]
                        else:
                            close_df = dp.xs("Close", axis=1, level=1)
                    else:
                        close_df = dp[["Close"]] if "Close" in dp.columns else dp

                    ret_df = close_df.pct_change().dropna()
                    na     = len(opt_tickers)
                    mu_r   = ret_df.mean()
                    cov    = ret_df.cov()
                    N      = 3000
                    vols, rets, sharpes, all_w = [], [], [], []

                    for _ in range(N):
                        w  = np.random.dirichlet(np.ones(na))
                        pr = float(np.dot(mu_r, w)) * 252
                        pv = float(np.sqrt(w @ (cov.values * 252) @ w))
                        ps = pr / pv if pv > 0 else 0
                        vols.append(pv); rets.append(pr); sharpes.append(ps); all_w.append(w)

                    max_sh_i = int(np.argmax(sharpes))
                    min_vl_i = int(np.argmin(vols))
                    obj = st.radio("Objective", ["Maximize Sharpe Ratio", "Minimize Volatility"], horizontal=True)
                    idx_sel = max_sh_i if "Sharpe" in obj else min_vl_i
                    opt_w = all_w[idx_sel]
                    sel_v = vols[idx_sel]; sel_r = rets[idx_sel]; sel_s = sharpes[idx_sel]

                    pm1, pm2, pm3 = st.columns(3)
                    pm1.markdown(f'<div class="glass-card"><p class="glass-label">Expected Annual Return</p><div class="glass-value" style="color:#00e87a;">{sel_r:.1%}</div></div>', unsafe_allow_html=True)
                    pm2.markdown(f'<div class="glass-card"><p class="glass-label">Annual Volatility</p><div class="glass-value" style="color:#ff3355;">{sel_v:.1%}</div></div>', unsafe_allow_html=True)
                    pm3.markdown(f'<div class="glass-card"><p class="glass-label">Sharpe Ratio</p><div class="glass-value" style="color:#00c8ff;">{sel_s:.2f}</div></div>', unsafe_allow_html=True)

                    st.markdown('<p class="section-header">[ CAPITAL ALLOCATION ]</p>', unsafe_allow_html=True)
                    colors_list = ["#00c8ff","#00e87a","#ffcc00","#ff6b35","#7c4dff","#ff3355","#fbbf24","#34d399","#a78bfa","#fb923c"]
                    alloc_cols = st.columns(min(len(opt_names), 5))
                    for i, (name, w) in enumerate(zip(opt_names, opt_w)):
                        amt = allocated_capital * w
                        clr = colors_list[i % len(colors_list)]
                        alloc_cols[i % min(len(opt_names), 5)].markdown(
                            f'<div class="glass-card" style="text-align:center;">'
                            f'<p class="glass-label">{name[:14]}</p>'
                            f'<div class="glass-value" style="color:{clr};font-size:.95rem;">₹{amt:,.0f}</div>'
                            f'<p style="font-size:10px;color:#6a90aa;margin:3px 0 0;">{w:.1%}</p></div>',
                            unsafe_allow_html=True
                        )

                    pc1, pc2 = st.columns(2)
                    with pc1:
                        fig_pie = go.Figure(data=[go.Pie(
                            labels=opt_names, values=opt_w, hole=0.42,
                            marker=dict(colors=colors_list[:len(opt_names)]),
                            textfont=dict(color="#ddeeff")
                        )])
                        fig_pie.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#ddeeff", family="Space Mono", size=10),
                            margin=dict(l=10, r=10, t=10, b=10))
                        st.plotly_chart(fig_pie, use_container_width=True)
                    with pc2:
                        fig_ef = go.Figure()
                        fig_ef.add_trace(go.Scatter(x=vols, y=rets, mode="markers",
                            marker=dict(color=sharpes, colorscale="Viridis", size=3, showscale=True,
                                        colorbar=dict(title="Sharpe", thickness=12,
                                                      titlefont=dict(color="#ddeeff", size=9),
                                                      tickfont=dict(color="#ddeeff", size=8))),
                            name="Portfolios"))
                        fig_ef.add_trace(go.Scatter(x=[sel_v], y=[sel_r], mode="markers",
                            marker=dict(color="#ff3355", size=14, symbol="star",
                                        line=dict(width=1, color="white")), name="Optimal"))
                        fig_ef.update_layout(height=300, paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)",
                            font=dict(color="#ddeeff", family="Space Mono", size=10),
                            xaxis=dict(title="Volatility", gridcolor="rgba(0,200,255,0.04)", tickformat=".1%"),
                            yaxis=dict(title="Return",     gridcolor="rgba(0,200,255,0.04)", tickformat=".1%"),
                            margin=dict(l=10, r=10, t=10, b=10),
                            legend=dict(bgcolor="rgba(7,18,32,0.5)", font=dict(size=9)))
                        st.plotly_chart(fig_ef, use_container_width=True)
                else:
                    st.error("Failed to load data.")
            except Exception as e:
                st.error(f"Portfolio error: {e}")

    st.markdown("---")
    st.markdown('<p class="section-header">[ 🎯 REAL PORTFOLIO EXIT STRATEGY PLANNER ]</p>', unsafe_allow_html=True)
    st.caption("Input details of any stock position you currently hold to receive an optimized exit strategy (Batch Scaling vs. Lump-Sum Exit vs Dynamic Trailing ATR Stop).")
    
    col_ex1, col_ex2 = st.columns([1, 1.5])
    with col_ex1:
        ex_ticker = st.text_input("Holding Symbol:", value="RELIANCE", key="ex_tick_input").upper()
        ex_entry  = st.number_input("Average Buy Price:", min_value=0.01, value=2400.0, step=10.0, key="ex_entry_input")
        ex_qty    = st.number_input("Shares Quantity:", min_value=1, value=50, step=5, key="ex_qty_input")
        ex_target = st.number_input("Target Price [Optional]:", min_value=0.0, value=2750.0, step=10.0, key="ex_tgt_input")
        ex_stop   = st.number_input("Stop-Loss Price [Optional]:", min_value=0.0, value=2250.0, step=10.0, key="ex_stop_input")

    with col_ex2:
        try:
            from engine.portfolio_exit import generate_exit_strategy
            from engine.data_loader import fetch_stock_data, calculate_indicators
            
            ex_sym_res = resolve_ticker(ex_ticker)
            ex_df = fetch_stock_data(ex_sym_res, period="6mo")
            if not ex_df.empty:
                ex_df = calculate_indicators(ex_df)
                curr_p = float(ex_df.iloc[-1]['close'])
            else:
                curr_p = ex_entry
                
            plan = generate_exit_strategy(
                ticker=ex_ticker, entry_price=ex_entry, quantity=ex_qty,
                current_price=curr_p, user_target=ex_target, user_stop_loss=ex_stop, df=ex_df
            )
            
            pnl_val = plan['pnl']
            pnl_clr = "#00e87a" if pnl_val >= 0 else "#ff3355"
            pnl_sign = "+" if pnl_val >= 0 else ""
            csym = plan.get('currency_symbol', '₹')
            
            st.markdown(f"""
            <div class="glass-card" style="border-left:4px solid {pnl_clr};">
                <div style="display:flex;justify-content:space-between;align-items:center;">
                    <div>
                        <p class="glass-label">UNREALIZED P&L</p>
                        <div class="glass-value" style="color:{pnl_clr};">{pnl_sign}{csym}{abs(pnl_val):,.2f} ({pnl_sign}{plan['pnl_pct']}%)</div>
                    </div>
                    <div style="text-align:right;">
                        <p class="glass-label">RECOMMENDED EXIT</p>
                        <div style="color:#00c8ff;font-family:'Space Mono',monospace;font-weight:700;font-size:1rem;">{plan['strategy_title']}</div>
                    </div>
                </div>
            </div>
            """, unsafe_allow_html=True)
            
            for r in plan['reasoning']:
                st.markdown(f"• {r}")
                
            st.table(pd.DataFrame(plan['tranches']))
        except Exception as e:
            st.info("Fill in your holding details on the left to compute your exit strategy.")
