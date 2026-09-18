import numpy as np
import pandas as pd
from data.storage import load_journal

def compute_position_sizing(
    capital: float, 
    risk_pct: float, 
    entry: float, 
    stop: float, 
    risk_reward: float = 2.0
) -> dict:
    """
    Compute ATR-based position sizing and Kelly Criterion.
    """
    if abs(entry - stop) < 1e-9:
        return {
            "shares": 0, "allocated_capital": 0.0, "pct_portfolio": 0.0,
            "kelly_fraction": 0.0, "suggested_kelly_capital": 0.0
        }
        
    # ATR Position Sizing
    risk_amt = capital * (risk_pct / 100.0)
    loss_per_share = abs(entry - stop)
    shares = int(risk_amt / loss_per_share)
    allocated = shares * entry
    pct_port = (allocated / capital) * 100.0
    
    # Kelly Criterion calculation
    # p = win rate, q = loss rate, b = risk:reward ratio
    # f* = p - q/b = p - (1-p)/b
    journal_df = load_journal()
    win_rate = 0.50 # default standard prior
    
    if len(journal_df) >= 3:
        try:
            pnl_vals = pd.to_numeric(journal_df["P&L (₹)"], errors="coerce").dropna()
            wins = (pnl_vals > 0).sum()
            total = len(pnl_vals)
            if total > 0:
                win_rate = float(wins / total)
        except Exception:
            pass
            
    b = risk_reward
    p = win_rate
    kelly_f = p - (1.0 - p) / (b + 1e-9)
    kelly_f = max(0.0, min(0.3, kelly_f)) # cap at 30% for risk safety (half-kelly style)
    
    suggested_kelly_cap = capital * kelly_f
    
    return {
        "shares": shares,
        "allocated_capital": round(allocated, 2),
        "pct_portfolio": round(pct_port, 2),
        "win_rate_used": round(win_rate * 100, 1),
        "kelly_fraction": round(kelly_f * 100, 2),
        "suggested_kelly_capital": round(suggested_kelly_cap, 2)
    }

def compute_var_cvar(returns: pd.Series, confidence_level: float = 0.95) -> tuple[float, float]:
    """
    Compute Value at Risk (VaR) and Conditional VaR (CVaR) using historical simulation.
    Returns percentage values.
    """
    clean_ret = returns.dropna()
    if len(clean_ret) < 20:
        return 0.0, 0.0
        
    # Historical VaR
    alpha = 1.0 - confidence_level
    var_val = np.percentile(clean_ret, alpha * 100)
    
    # Historical CVaR (expected shortfall)
    cvar_val = clean_ret[clean_ret <= var_val].mean()
    
    # Return as positive percentage loss
    return round(-var_val * 100, 2), round(-cvar_val * 100, 2)

def compute_max_drawdown(prices: pd.Series) -> float:
    """Compute maximum peak-to-trough drawdown of a price series (%)."""
    clean_p = prices.dropna()
    if len(clean_p) < 2:
        return 0.0
    cum_max = clean_p.cummax()
    drawdowns = (clean_p - cum_max) / (cum_max + 1e-9)
    return round(float(drawdowns.min() * 100), 2)

def compute_portfolio_risk_metrics(
    portfolio_df: pd.DataFrame, 
    returns_matrix: pd.DataFrame, 
    benchmark_returns: pd.Series
) -> dict:
    """
    Compute Portfolio Beta, Sector Concentration, and VaR/CVaR.
    - portfolio_df: Columns: ['Ticker', 'Shares', 'Price', 'Sector']
    - returns_matrix: DataFrame of returns with Ticker as columns
    - benchmark_returns: Series of returns for the market index
    """
    if portfolio_df.empty:
        return {
            "beta": 1.0, "var_95": 0.0, "cvar_95": 0.0,
            "sector_concentration": {}, "max_drawdown": 0.0
        }
        
    portfolio_df = portfolio_df.copy()
    portfolio_df["Value"] = portfolio_df["Shares"] * portfolio_df["Price"]
    total_val = portfolio_df["Value"].sum()
    portfolio_df["Weight"] = portfolio_df["Value"] / (total_val + 1e-9)
    
    # Sector Concentration
    sector_alloc = portfolio_df.groupby("Sector")["Weight"].sum().to_dict()
    sector_alloc = {k: round(v * 100, 2) for k, v in sector_alloc.items()}
    
    # If returns matrix is empty, return simple allocation details
    if returns_matrix.empty or len(returns_matrix) < 10:
        return {
            "beta": 1.0, "var_95": 0.0, "cvar_95": 0.0,
            "sector_concentration": sector_alloc, "max_drawdown": 0.0
        }
        
    # Portfolio Returns
    weights = []
    tickers = []
    for idx, row in portfolio_df.iterrows():
        t = row["Ticker"]
        if t in returns_matrix.columns:
            weights.append(row["Weight"])
            tickers.append(t)
            
    if not weights:
        return {
            "beta": 1.0, "var_95": 0.0, "cvar_95": 0.0,
            "sector_concentration": sector_alloc, "max_drawdown": 0.0
        }
        
    # Normalized weights
    w_arr = np.array(weights) / sum(weights)
    p_returns = returns_matrix[tickers].dot(w_arr)
    
    # Portfolio VaR and CVaR
    var_95, cvar_95 = compute_var_cvar(p_returns, 0.95)
    
    # Portfolio Beta
    p_beta = 1.0
    if benchmark_returns is not None and len(benchmark_returns) == len(p_returns):
        try:
            cov = p_returns.cov(benchmark_returns)
            var = benchmark_returns.var()
            p_beta = cov / (var + 1e-9)
        except Exception:
            pass
            
    # Portfolio Max Drawdown (constructed historical path)
    cum_ret = (1 + p_returns).cumprod()
    max_dd = compute_max_drawdown(cum_ret)
    
    return {
        "beta": round(p_beta, 2),
        "var_95": var_95,
        "cvar_95": cvar_95,
        "sector_concentration": sector_alloc,
        "max_drawdown": max_dd
    }
