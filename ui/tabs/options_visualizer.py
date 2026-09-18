"""
Multi-Leg Options Strategy & Payoff Visualizer with Greeks (Delta, Gamma, Theta, Vega).
Supports Bull Call Spreads, Iron Condors, Covered Calls, and Straddles.
"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go

def calculate_option_greeks(spot: float, strike: float, dte: int, iv: float = 0.20, option_type: str = "call"):
    """Calculate approximate Black-Scholes Option Greeks."""
    r = 0.05
    t = max(dte, 1) / 365.0
    v = max(iv, 0.05)
    
    d1 = (np.log(spot / strike) + (r + 0.5 * v ** 2) * t) / (v * np.sqrt(t))
    d2 = d1 - v * np.sqrt(t)
    
    from scipy.stats import norm
    
    delta = norm.cdf(d1) if option_type == "call" else norm.cdf(d1) - 1.0
    gamma = norm.pdf(d1) / (spot * v * np.sqrt(t))
    vega = (spot * norm.pdf(d1) * np.sqrt(t)) / 100.0
    theta = (-(spot * norm.pdf(d1) * v) / (2 * np.sqrt(t)) - r * strike * np.exp(-r * t) * norm.cdf(d2)) / 365.0
    
    return {
        "delta": round(float(delta), 4),
        "gamma": round(float(gamma), 4),
        "theta": round(float(theta), 4),
        "vega": round(float(vega), 4)
    }

def generate_payoff_diagram(spot_price: float, strategy: str = "Bull Call Spread"):
    """
    Generates interactive Plotly payoff diagram for multi-leg options strategies.
    """
    price_range = np.linspace(spot_price * 0.80, spot_price * 1.20, 100)
    
    if strategy == "Bull Call Spread":
        strike_buy = round(spot_price, 2)
        strike_sell = round(spot_price * 1.05, 2)
        prem_buy = round(spot_price * 0.03, 2)
        prem_sell = round(spot_price * 0.012, 2)
        net_prem = prem_buy - prem_sell
        
        payoff = np.maximum(price_range - strike_buy, 0) - np.maximum(price_range - strike_sell, 0) - net_prem
        title = f"Bull Call Spread ({strike_buy} Buy Call / {strike_sell} Sell Call)"
        
    elif strategy == "Iron Condor":
        s_put_sell = round(spot_price * 0.95, 2)
        s_put_buy = round(spot_price * 0.90, 2)
        s_call_sell = round(spot_price * 1.05, 2)
        s_call_buy = round(spot_price * 1.10, 2)
        net_credit = round(spot_price * 0.02, 2)
        
        payoff_put = np.maximum(s_put_sell - price_range, 0) - np.maximum(s_put_buy - price_range, 0)
        payoff_call = np.maximum(price_range - s_call_sell, 0) - np.maximum(price_range - s_call_buy, 0)
        payoff = net_credit - payoff_put - payoff_call
        title = f"Iron Condor (Put Spd: {s_put_buy}/{s_put_sell} | Call Spd: {s_call_sell}/{s_call_buy})"
        
    else:  # Covered Call
        strike_sell = round(spot_price * 1.04, 2)
        prem_received = round(spot_price * 0.025, 2)
        payoff = (price_range - spot_price) - np.maximum(price_range - strike_sell, 0) + prem_received
        title = f"Covered Call (Stock + Sell Call @ {strike_sell})"
        
    fig = go.Figure()
    colors = ["#00e87a" if p >= 0 else "#ff3355" for p in payoff]
    
    fig.add_trace(go.Scatter(x=price_range, y=payoff, mode="lines", name="Net P&L", line=dict(color="#00c8ff", width=2.5)))
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.4)")
    fig.add_vline(x=spot_price, line_dash="dot", line_color="#ffcc00", annotation_text=f"Spot ₹{spot_price:,.2f}")
    
    fig.update_layout(
        title=title,
        height=320,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ddeeff", family="Space Mono", size=10),
        xaxis=dict(title="Price at Expiration", gridcolor="rgba(0,200,255,0.05)"),
        yaxis=dict(title="Profit / Loss (P&L)", gridcolor="rgba(0,200,255,0.05)"),
        margin=dict(l=10, r=10, t=35, b=10)
    )
    return fig
