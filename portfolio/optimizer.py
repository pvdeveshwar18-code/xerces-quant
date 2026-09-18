import numpy as np
import pandas as pd
from scipy.optimize import minimize

def run_mean_variance_optimization(
    tickers: list[str], 
    returns_matrix: pd.DataFrame, 
    rf_rate: float = 0.0,
    target: str = "sharpe", # "sharpe", "min_vol"
    bounds: tuple = (0.0, 0.4) # min, max weight per stock
) -> tuple[dict[str, float], float, float]:
    """
    Mean-Variance Optimization.
    Returns weights dictionary, expected portfolio return, and portfolio volatility.
    """
    if not tickers or returns_matrix.empty:
        return {}, 0.0, 0.0
        
    valid_tickers = [t for t in tickers if t in returns_matrix.columns]
    if len(valid_tickers) < 2:
        return {t: 1.0 for t in valid_tickers}, 0.0, 0.0
        
    rets = returns_matrix[valid_tickers]
    mean_rets = rets.mean() * 252
    cov_matrix = rets.cov() * 252
    n = len(valid_tickers)
    
    # Define optimization objectives
    def portfolio_performance(w):
        p_ret = np.sum(mean_rets * w)
        p_vol = np.sqrt(np.dot(w.T, np.dot(cov_matrix, w)))
        return p_ret, p_vol
        
    def min_vol_obj(w):
        return portfolio_performance(w)[1]
        
    def max_sharpe_obj(w):
        p_ret, p_vol = portfolio_performance(w)
        return -(p_ret - rf_rate) / (p_vol + 1e-9)
        
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
    init_weights = np.array([1.0 / n] * n)
    bnds = [bounds] * n
    
    obj = max_sharpe_obj if target == "sharpe" else min_vol_obj
    res = minimize(obj, init_weights, method="SLSQP", bounds=bnds, constraints=constraints)
    
    if not res.success:
        # Fallback to equal weights
        weights = init_weights
    else:
        weights = res.x
        
    opt_ret, opt_vol = portfolio_performance(weights)
    weights_dict = {valid_tickers[i]: float(weights[i]) for i in range(n)}
    
    return weights_dict, opt_ret, opt_vol

def run_black_litterman_optimization(
    tickers: list[str],
    returns_matrix: pd.DataFrame,
    market_weights: dict[str, float], # prior market cap weights
    views: list[dict], # list of view dicts: {'asset': str, 'direction': float, 'confidence': float} (e.g. +5% return)
    rf_rate: float = 0.0,
    risk_aversion: float = 2.5
) -> tuple[dict[str, float], np.ndarray]:
    """
    Black-Litterman Portfolio Optimization.
    Priors from market weights, combined with subjective investor views.
    """
    if not tickers or returns_matrix.empty:
        return {}, np.array([])
        
    valid_tickers = [t for t in tickers if t in returns_matrix.columns]
    n = len(valid_tickers)
    if n < 2:
        return {t: 1.0 for t in valid_tickers}, np.array([])
        
    rets = returns_matrix[valid_tickers]
    cov = rets.cov().values * 252 # Annualized covariance
    
    # 1. Prior Market Weights (w_mkt)
    w_mkt = np.array([market_weights.get(t, 1.0 / n) for t in valid_tickers])
    w_mkt = w_mkt / sum(w_mkt) # normalize
    
    # Implied Equilibrium Excess Returns (Pi)
    # Pi = delta * Sigma * w_mkt
    Pi = risk_aversion * np.dot(cov, w_mkt)
    
    # 2. Incorporate Views
    # P: view matrix, Q: view targets, Omega: view uncertainty covariance
    if not views:
        # No views -> returns equilibrium
        post_rets = Pi + rf_rate
    else:
        # Construct P, Q, Omega
        P = []
        Q = []
        omega_diag = []
        tau = 0.05 # Scaling parameter for covariance matrix uncertainty
        
        for view in views:
            asset = view.get("asset")
            if asset in valid_tickers:
                # Absolute view on a single asset
                p_row = np.zeros(n)
                idx = valid_tickers.index(asset)
                p_row[idx] = 1.0
                P.append(p_row)
                Q.append(view["direction"])
                
                # Omega variance based on confidence (higher confidence -> lower variance)
                conf = view.get("confidence", 0.5)
                # Variance = tau * (p_i * Sigma * p_i^T) * ((1 - conf) / conf)
                asset_var = cov[idx, idx]
                var_omega = tau * asset_var * max(0.01, (1.0 - conf) / (conf + 1e-9))
                omega_diag.append(var_omega)
                
        if not P:
            post_rets = Pi + rf_rate
        else:
            P = np.array(P)
            Q = np.array(Q)
            Omega = np.diag(omega_diag)
            
            # Black-Litterman formula:
            # E[R] = Pi + tau * Sigma * P^T * (P * tau * Sigma * P^T + Omega)^-1 * (Q - P * Pi)
            tau_Sigma = tau * cov
            try:
                middle = np.linalg.inv(np.dot(P, np.dot(tau_Sigma, P.T)) + Omega)
                link = np.dot(tau_Sigma, np.dot(P.T, middle))
                excess_post_rets = Pi + np.dot(link, (Q - np.dot(P, Pi)))
                post_rets = excess_post_rets + rf_rate
            except Exception:
                post_rets = Pi + rf_rate
                
    # 3. Solve for optimal weights using SLSQP with sum-to-one constraint
    def bl_sharpe_obj(w):
        p_ret = np.sum(post_rets * w)
        p_vol = np.sqrt(np.dot(w.T, np.dot(cov, w)))
        return -(p_ret - rf_rate) / (p_vol + 1e-9)
        
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
    bnds = [(0.0, 0.4)] * n
    init_weights = np.array([1.0 / n] * n)
    res = minimize(bl_sharpe_obj, init_weights, method="SLSQP", bounds=bnds, constraints=constraints)
    
    if not res.success:
        opt_weights = w_mkt
    else:
        opt_weights = res.x
        
    weights_dict = {valid_tickers[i]: float(opt_weights[i]) for i in range(n)}
    return weights_dict, post_rets

def run_risk_parity_optimization(
    tickers: list[str], 
    returns_matrix: pd.DataFrame
) -> dict[str, float]:
    """
    Risk Parity Portfolio Optimization.
    Equalizes the risk contribution of each asset.
    """
    if not tickers or returns_matrix.empty:
        return {}
        
    valid_tickers = [t for t in tickers if t in returns_matrix.columns]
    n = len(valid_tickers)
    if n < 2:
        return {t: 1.0 for t in valid_tickers}
        
    cov = returns_matrix[valid_tickers].cov().values * 252
    
    # Risk Parity Objective: Minimize variance of risk contributions
    def risk_parity_objective(w):
        # Portfolio volatility
        p_vol = np.sqrt(np.dot(w.T, np.dot(cov, w)))
        # Marginal risk contribution
        mrc = np.dot(cov, w) / (p_vol + 1e-9)
        # Risk contribution
        rc = w * mrc
        # Variance of risk contributions
        diff = rc - (p_vol / n)
        return np.sum(diff ** 2)
        
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
    # Long-only bounds
    bnds = [(0.01, 0.6)] * n
    init_weights = np.array([1.0 / n] * n)
    
    res = minimize(risk_parity_objective, init_weights, method="SLSQP", bounds=bnds, constraints=constraints)
    
    if not res.success:
        weights = init_weights
    else:
        weights = res.x
        
    weights = weights / sum(weights) # re-normalize
    return {valid_tickers[i]: float(weights[i]) for i in range(n)}

def run_max_diversification_optimization(
    tickers: list[str], 
    returns_matrix: pd.DataFrame
) -> dict[str, float]:
    """
    Maximum Diversification Portfolio Optimization.
    Maximizes the diversification ratio: DR = (w^T * sigma) / sqrt(w^T * Sigma * w)
    """
    if not tickers or returns_matrix.empty:
        return {}
        
    valid_tickers = [t for t in tickers if t in returns_matrix.columns]
    n = len(valid_tickers)
    if n < 2:
        return {t: 1.0 for t in valid_tickers}
        
    cov = returns_matrix[valid_tickers].cov().values * 252
    vols = np.sqrt(np.diag(cov))
    
    def diversification_ratio_neg(w):
        weighted_vol = np.sum(w * vols)
        p_vol = np.sqrt(np.dot(w.T, np.dot(cov, w)))
        return -weighted_vol / (p_vol + 1e-9)
        
    constraints = {"type": "eq", "fun": lambda w: np.sum(w) - 1.0}
    bnds = [(0.0, 0.5)] * n
    init_weights = np.array([1.0 / n] * n)
    
    res = minimize(diversification_ratio_neg, init_weights, method="SLSQP", bounds=bnds, constraints=constraints)
    
    if not res.success:
        weights = init_weights
    else:
        weights = res.x
        
    return {valid_tickers[i]: float(weights[i]) for i in range(n)}
