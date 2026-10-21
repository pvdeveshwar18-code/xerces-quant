"""
Multi-Leg Options Strategy & Payoff Visualizer with Greeks (Delta, Gamma, Theta, Vega).
Supports Bull Call Spreads, Bear Put Spreads, Iron Condors, Straddles, Strangles,
Covered Calls, and Protective Puts with Expiry + T+0 Curves and Break-Even Analysis.
"""

from typing import Dict, Any, Tuple, List
import numpy as np
import pandas as pd
import plotly.graph_objects as go
from scipy.stats import norm

def calculate_option_greeks(
    spot: float,
    strike: float,
    dte: int,
    iv: float = 0.20,
    option_type: str = "call",
    r: float = 0.05
) -> Dict[str, float]:
    """Calculate approximate Black-Scholes Option Greeks."""
    t = max(dte, 0.5) / 365.0
    v = max(iv, 0.05)
    
    d1 = (np.log(spot / strike) + (r + 0.5 * v ** 2) * t) / (v * np.sqrt(t))
    d2 = d1 - v * np.sqrt(t)
    
    delta = norm.cdf(d1) if option_type == "call" else norm.cdf(d1) - 1.0
    gamma = norm.pdf(d1) / (spot * v * np.sqrt(t))
    vega = (spot * norm.pdf(d1) * np.sqrt(t)) / 100.0
    theta = (-(spot * norm.pdf(d1) * v) / (2 * np.sqrt(t)) - r * strike * np.exp(-r * t) * (norm.cdf(d2) if option_type == "call" else norm.cdf(-d2))) / 365.0
    
    # Theoretical premium
    if option_type == "call":
        premium = spot * norm.cdf(d1) - strike * np.exp(-r * t) * norm.cdf(d2)
    else:
        premium = strike * np.exp(-r * t) * norm.cdf(-d2) - spot * norm.cdf(-d1)

    return {
        "delta": round(float(delta), 4),
        "gamma": round(float(gamma), 6),
        "theta": round(float(theta), 4),
        "vega": round(float(vega), 4),
        "premium": round(float(premium), 2),
    }

def generate_payoff_diagram(
    spot_price: float,
    strategy: str = "Bull Call Spread",
    dte: int = 30,
    iv: float = 0.25,
) -> Tuple[go.Figure, Dict[str, Any]]:
    """
    Generates interactive Plotly payoff diagram and comprehensive analytics
    for multi-leg options strategies, including Expiry Payoff, T+0 Curve, Breakevens,
    and Net Portfolio Greeks.
    """
    price_range = np.linspace(spot_price * 0.75, spot_price * 1.25, 200)
    legs = []  # list of tuples: (option_type, strike, position_multiplier +1/-1 or 'stock')

    if strategy == "Bull Call Spread":
        k_buy = round(spot_price, 1)
        k_sell = round(spot_price * 1.05, 1)
        legs = [("call", k_buy, 1), ("call", k_sell, -1)]
        title = f"Bull Call Spread (Buy {k_buy} CE / Sell {k_sell} CE)"

    elif strategy == "Bear Put Spread":
        k_buy = round(spot_price, 1)
        k_sell = round(spot_price * 0.95, 1)
        legs = [("put", k_buy, 1), ("put", k_sell, -1)]
        title = f"Bear Put Spread (Buy {k_buy} PE / Sell {k_sell} PE)"

    elif strategy == "Iron Condor":
        p_buy = round(spot_price * 0.90, 1)
        p_sell = round(spot_price * 0.95, 1)
        c_sell = round(spot_price * 1.05, 1)
        c_buy = round(spot_price * 1.10, 1)
        legs = [("put", p_buy, 1), ("put", p_sell, -1), ("call", c_sell, -1), ("call", c_buy, 1)]
        title = f"Iron Condor ({p_buy}P/{p_sell}P · {c_sell}C/{c_buy}C)"

    elif strategy == "Long Straddle":
        k_atm = round(spot_price, 1)
        legs = [("call", k_atm, 1), ("put", k_atm, 1)]
        title = f"Long Straddle (Buy {k_atm} CE + {k_atm} PE)"

    elif strategy == "Long Strangle":
        k_put = round(spot_price * 0.96, 1)
        k_call = round(spot_price * 1.04, 1)
        legs = [("put", k_put, 1), ("call", k_call, 1)]
        title = f"Long Strangle (Buy {k_put} PE + {k_call} CE)"

    elif strategy == "Protective Put":
        k_put = round(spot_price * 0.95, 1)
        legs = [("stock", spot_price, 1), ("put", k_put, 1)]
        title = f"Protective Put (Long Stock + Buy {k_put} PE)"

    else:  # Covered Call
        k_call = round(spot_price * 1.04, 1)
        legs = [("stock", spot_price, 1), ("call", k_call, -1)]
        title = f"Covered Call (Long Stock + Sell {k_call} CE)"

    # Compute Net Greeks and Premiums
    net_delta = 0.0
    net_gamma = 0.0
    net_theta = 0.0
    net_vega = 0.0
    net_premium_cost = 0.0

    payoff_expiry = np.zeros_like(price_range)
    payoff_t0 = np.zeros_like(price_range)

    for leg in legs:
        l_type, l_strike, l_pos = leg
        if l_type == "stock":
            net_delta += 1.0 * l_pos
            payoff_expiry += (price_range - spot_price) * l_pos
            payoff_t0 += (price_range - spot_price) * l_pos
        else:
            g = calculate_option_greeks(spot=spot_price, strike=l_strike, dte=dte, iv=iv, option_type=l_type)
            net_delta += g["delta"] * l_pos
            net_gamma += g["gamma"] * l_pos
            net_theta += g["theta"] * l_pos
            net_vega += g["vega"] * l_pos
            net_premium_cost += g["premium"] * l_pos

            # Expiry Payoff
            if l_type == "call":
                payoff_expiry += (np.maximum(price_range - l_strike, 0) - g["premium"]) * l_pos
            else:
                payoff_expiry += (np.maximum(l_strike - price_range, 0) - g["premium"]) * l_pos

            # T+0 Payoff curve (Current DTE)
            t0_prems = [calculate_option_greeks(spot=p, strike=l_strike, dte=dte, iv=iv, option_type=l_type)["premium"] for p in price_range]
            payoff_t0 += (np.array(t0_prems) - g["premium"]) * l_pos

    # Calculate Max Profit, Max Loss, Breakevens
    max_profit = float(np.max(payoff_expiry))
    max_loss = float(np.min(payoff_expiry))
    
    # Find Zero Crossings (Breakevens)
    signs = np.sign(payoff_expiry)
    cross_indices = np.where(np.diff(signs))[0]
    breakevens = [round(float(price_range[idx]), 1) for idx in cross_indices]

    rr_ratio = abs(max_profit / max_loss) if max_loss < 0 else 999.0

    # Build Interactive Plotly Payoff Chart
    fig = go.Figure()

    # Expiry Payoff (Solid Green/Red)
    fig.add_trace(go.Scatter(
        x=price_range,
        y=payoff_expiry,
        mode="lines",
        name="At Expiration Payoff",
        line=dict(color="#00e87a", width=2.5)
    ))

    # T+0 Payoff Curve (Cyan Dashed Line)
    fig.add_trace(go.Scatter(
        x=price_range,
        y=payoff_t0,
        mode="lines",
        name=f"T+0 Payoff (DTE: {dte})",
        line=dict(color="#00c8ff", width=1.8, dash="dot")
    ))

    # Zero Line
    fig.add_hline(y=0, line_dash="dash", line_color="rgba(255,255,255,0.4)")
    # Spot Price Vertical Line
    fig.add_vline(x=spot_price, line_dash="dot", line_color="#ffcc00",
                  annotation_text=f"Spot ₹{spot_price:,.1f}", annotation_position="top left")

    # Breakeven markers
    for be in breakevens:
        fig.add_vline(x=be, line_dash="dash", line_color="#ff66aa",
                      annotation_text=f"BE ₹{be:,.1f}", annotation_position="bottom right")

    fig.update_layout(
        title=dict(text=title, font=dict(color="#00c8ff", size=13)),
        height=340,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(color="#ddeeff", family="Space Mono", size=10),
        legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1),
        xaxis=dict(title="Asset Price at Expiry", gridcolor="rgba(0,200,255,0.05)"),
        yaxis=dict(title="Net P&L (₹)", gridcolor="rgba(0,200,255,0.05)"),
        margin=dict(l=10, r=10, t=35, b=10)
    )

    metrics = {
        "strategy": strategy,
        "max_profit": max_profit,
        "max_loss": max_loss,
        "risk_reward": round(rr_ratio, 2),
        "breakevens": breakevens,
        "net_premium": round(net_premium_cost, 2),
        "net_delta": round(net_delta, 4),
        "net_gamma": round(net_gamma, 6),
        "net_theta": round(net_theta, 4),
        "net_vega": round(net_vega, 4),
    }

    return fig, metrics
