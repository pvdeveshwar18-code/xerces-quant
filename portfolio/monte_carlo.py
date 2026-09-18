import numpy as np
import pandas as pd

def simulate_portfolio_paths(
    weights_dict: dict[str, float], 
    returns_matrix: pd.DataFrame, 
    steps: int = 60, 
    num_simulations: int = 10000,
    initial_value: float = 100000.0
) -> dict:
    """
    Simulate future portfolio paths using Monte Carlo simulation.
    Generates simulated paths based on asset mean returns and covariance matrix.
    """
    if not weights_dict or returns_matrix.empty:
        return {}
        
    tickers = list(weights_dict.keys())
    valid_tickers = [t for t in tickers if t in returns_matrix.columns]
    
    if not valid_tickers:
        return {}
        
    rets = returns_matrix[valid_tickers]
    mean_rets = rets.mean().values
    cov_matrix = rets.cov().values
    
    weights = np.array([weights_dict[t] for t in valid_tickers])
    weights = weights / (sum(weights) + 1e-9) # Normalize
    
    # Portfolio expected daily return and daily volatility
    port_mean = np.dot(weights, mean_rets)
    port_var = np.dot(weights.T, np.dot(cov_matrix, weights))
    port_std = np.sqrt(port_var)
    
    # Generate daily simulated returns: shape (steps, num_simulations)
    # Using geometric brownian motion / normal distribution for returns
    sim_returns = np.random.normal(port_mean, port_std, size=(steps, num_simulations))
    
    # Calculate cumulative portfolio value path: shape (steps + 1, num_simulations)
    paths = np.ones((steps + 1, num_simulations)) * initial_value
    for t in range(1, steps + 1):
        paths[t] = paths[t - 1] * (1 + sim_returns[t - 1])
        
    # Calculate key percentiles for visualization
    p5 = np.percentile(paths, 5, axis=1)
    p50 = np.percentile(paths, 50, axis=1)
    p95 = np.percentile(paths, 95, axis=1)
    
    final_values = paths[-1]
    prob_loss = float(np.mean(final_values < initial_value) * 100)
    expected_shortfall = float(final_values[final_values < initial_value].mean() if any(final_values < initial_value) else initial_value)
    
    return {
        "p5": p5,
        "p50": p50,
        "p95": p95,
        "raw_paths_sample": paths[:, :100], # return a sample of 100 paths for plotting
        "prob_loss": prob_loss,
        "expected_shortfall": expected_shortfall,
        "median_final_value": p50[-1],
        "upside_95_final_value": p95[-1],
        "downside_5_final_value": p5[-1],
        "initial_value": initial_value
    }
