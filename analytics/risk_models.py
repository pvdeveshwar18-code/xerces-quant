import numpy as np
import pandas as pd

def compute_cvar(df: pd.DataFrame, confidence_level: float = 0.95, portfolio_value: float = 100000.0) -> dict:
    """
    Compute Value-at-Risk (VaR) and Conditional Value-at-Risk (CVaR / Expected Shortfall)
    using historical simulation.
    """
    if len(df) < 30:
        return {
            "var_95_pct": 0.0, "var_95_inr": 0.0,
            "cvar_95_pct": 0.0, "cvar_95_inr": 0.0,
            "var_99_pct": 0.0, "var_99_inr": 0.0,
            "cvar_99_pct": 0.0, "cvar_99_inr": 0.0,
        }

    returns = df["Close"].astype(float).pct_change().dropna()

    # VaR & CVaR at 95% confidence
    cutoff_95 = np.percentile(returns, (1 - 0.95) * 100)
    var_95_pct = abs(float(cutoff_95))
    cvar_95_pct = abs(float(returns[returns <= cutoff_95].mean())) if len(returns[returns <= cutoff_95]) > 0 else var_95_pct

    # VaR & CVaR at 99% confidence
    cutoff_99 = np.percentile(returns, (1 - 0.99) * 100)
    var_99_pct = abs(float(cutoff_99))
    cvar_99_pct = abs(float(returns[returns <= cutoff_99].mean())) if len(returns[returns <= cutoff_99]) > 0 else var_99_pct

    return {
        "var_95_pct": round(var_95_pct * 100, 2),
        "var_95_inr": round(var_95_pct * portfolio_value, 2),
        "cvar_95_pct": round(cvar_95_pct * 100, 2),
        "cvar_95_inr": round(cvar_95_pct * portfolio_value, 2),
        "var_99_pct": round(var_99_pct * 100, 2),
        "var_99_inr": round(var_99_pct * portfolio_value, 2),
        "cvar_99_pct": round(cvar_99_pct * 100, 2),
        "cvar_99_inr": round(cvar_99_pct * portfolio_value, 2),
    }

def run_historical_stress_test(df: pd.DataFrame, portfolio_value: float = 100000.0) -> list[dict]:
    """
    Simulate portfolio/stock loss under 3 historical market crisis scenarios:
    1. 2008 Global Financial Crisis (-45% market shock, High Volatility)
    2. 2020 COVID Market Crash (-38% market shock, Panic Selloff)
    3. 2022 Inflation & Rate Hike Drawdown (-22% tech/growth shock)
    """
    if len(df) < 60:
        vol = 0.20
        beta = 1.0
    else:
        returns = df["Close"].astype(float).pct_change().dropna()
        vol = float(returns.std() * np.sqrt(252))
        beta = min(2.5, max(0.5, vol / 0.18))

    scenarios = [
        {
            "scenario": "2008 Global Financial Crisis",
            "market_shock_pct": -45.0,
            "stock_impact_pct": round(-45.0 * beta, 1),
            "estimated_loss_inr": round(portfolio_value * (abs(-45.0 * beta) / 100.0), 2),
            "severity": "CRITICAL",
            "color": "#ff3355"
        },
        {
            "scenario": "2020 COVID Liquidity Crash",
            "market_shock_pct": -38.0,
            "stock_impact_pct": round(-38.0 * beta, 1),
            "estimated_loss_inr": round(portfolio_value * (abs(-38.0 * beta) / 100.0), 2),
            "severity": "HIGH",
            "color": "#ff6b35"
        },
        {
            "scenario": "2022 Inflation & Rate Hike Spike",
            "market_shock_pct": -22.0,
            "stock_impact_pct": round(-22.0 * beta, 1),
            "estimated_loss_inr": round(portfolio_value * (abs(-22.0 * beta) / 100.0), 2),
            "severity": "MODERATE",
            "color": "#ffcc00"
        }
    ]

    return scenarios
