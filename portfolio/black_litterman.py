"""
XERCES Institutional Portfolio Engine — Black-Litterman Model
Blends Market Equilibrium Returns with Custom Investor Views to compute posterior returns & optimal weights.
"""

import numpy as np
import pandas as pd
import scipy.optimize as sco

class BlackLittermanEngine:
    """
    Implements full Black-Litterman Portfolio Optimization model.
    """

    @staticmethod
    def optimize_portfolio(returns_df: pd.DataFrame, views: list = None, risk_aversion: float = 2.5, tau: float = 0.05, risk_free_rate: float = 0.065) -> dict:
        """
        returns_df: DataFrame of asset historical daily returns (columns = ticker names)
        views: List of dicts representing investor views e.g.
               [{'type': 'absolute', 'asset': 'RELIANCE.NS', 'return': 0.18, 'confidence': 0.8},
                {'type': 'relative', 'asset_long': 'TCS.NS', 'asset_short': 'INFY.NS', 'return': 0.05, 'confidence': 0.7}]
        """
        tickers = list(returns_df.columns)
        n = len(tickers)
        if n < 2:
            raise ValueError("Black-Litterman optimization requires at least 2 assets.")

        # 1. Calculate Covariance Matrix (Annualized)
        cov_matrix = returns_df.cov() * 252
        sigma = cov_matrix.values

        # 2. Market Benchmark Weights (Equal Weighted prior or market cap prior)
        w_prior = np.ones(n) / n

        # 3. Implied Equilibrium Returns (Pi = lambda * Sigma * w_prior)
        pi = risk_aversion * np.dot(sigma, w_prior) + risk_free_rate

        # If no custom views provided, return Market Equilibrium Weights
        if not views:
            mu_bl = pi
            sigma_bl = sigma
        else:
            k = len(views)
            P = np.zeros((k, n))
            Q = np.zeros(k)
            omega_diag = []

            for idx, view in enumerate(views):
                conf = view.get('confidence', 0.5)
                # Variance penalty based on confidence
                conf_penalty = (1.0 - conf) / (conf + 1e-4)
                
                if view['type'] == 'absolute' and view['asset'] in tickers:
                    asset_idx = tickers.index(view['asset'])
                    P[idx, asset_idx] = 1.0
                    Q[idx] = view['return']
                    view_var = tau * np.dot(P[idx], np.dot(sigma, P[idx].T)) * (1.0 + conf_penalty)
                    omega_diag.append(view_var)
                elif view['type'] == 'relative' and view.get('asset_long') in tickers and view.get('asset_short') in tickers:
                    idx_long = tickers.index(view['asset_long'])
                    idx_short = tickers.index(view['asset_short'])
                    P[idx, idx_long] = 1.0
                    P[idx, idx_short] = -1.0
                    Q[idx] = view['return']
                    view_var = tau * np.dot(P[idx], np.dot(sigma, P[idx].T)) * (1.0 + conf_penalty)
                    omega_diag.append(view_var)
                else:
                    omega_diag.append(1.0)

            Omega = np.diag(omega_diag)

            # 4. Black-Litterman Master Equations
            tau_sigma = tau * sigma
            inv_tau_sigma = np.linalg.inv(tau_sigma)
            inv_Omega = np.linalg.inv(Omega)

            # Posterior Mean Vector: mu_bl = [(tau*Sigma)^-1 + P^T Omega^-1 P]^-1 * [(tau*Sigma)^-1 * Pi + P^T Omega^-1 Q]
            middle_term = inv_tau_sigma + np.dot(P.T, np.dot(inv_Omega, P))
            inv_middle = np.linalg.inv(middle_term)
            
            right_term = np.dot(inv_tau_sigma, pi) + np.dot(P.T, np.dot(inv_Omega, Q))
            mu_bl = np.dot(inv_middle, right_term)

            # Posterior Covariance Matrix: Sigma_bl = Sigma + inv(inv(tau*Sigma) + P^T Omega^-1 P)
            sigma_bl = sigma + inv_middle

        # 5. Calculate Max Sharpe Allocation with Posterior Estimates
        def neg_sharpe(weights):
            port_return = np.sum(weights * mu_bl)
            port_vol = np.sqrt(np.dot(weights.T, np.dot(sigma_bl, weights)))
            return - (port_return - risk_free_rate) / (port_vol + 1e-8)

        constraints = ({'type': 'eq', 'fun': lambda w: np.sum(w) - 1.0})
        bounds = tuple((0.0, 0.40) for _ in range(n)) # Max 40% per asset limit
        init_weights = np.ones(n) / n

        opt = sco.minimize(neg_sharpe, init_weights, method='SLSQP', bounds=bounds, constraints=constraints)
        opt_weights = opt.x if opt.success else init_weights

        # Output Summary
        expected_return = np.sum(opt_weights * mu_bl)
        expected_vol = np.sqrt(np.dot(opt_weights.T, np.dot(sigma_bl, opt_weights)))
        sharpe_ratio = (expected_return - risk_free_rate) / expected_vol

        weights_dict = {tickers[i]: round(float(opt_weights[i] * 100), 2) for i in range(n)}
        prior_returns_dict = {tickers[i]: round(float(pi[i] * 100), 2) for i in range(n)}
        bl_returns_dict = {tickers[i]: round(float(mu_bl[i] * 100), 2) for i in range(n)}

        return {
            "weights_pct": weights_dict,
            "prior_equilibrium_returns_pct": prior_returns_dict,
            "bl_posterior_returns_pct": bl_returns_dict,
            "portfolio_expected_return_pct": round(float(expected_return * 100), 2),
            "portfolio_volatility_pct": round(float(expected_vol * 100), 2),
            "portfolio_sharpe_ratio": round(float(sharpe_ratio), 2)
        }
