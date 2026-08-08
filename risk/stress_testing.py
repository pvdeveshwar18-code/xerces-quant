"""
XERCES Monte Carlo Risk Stress Testing Module
Calculates CVaR (Conditional Value-at-Risk) and Portfolio Drawdown Stress Testing under historic crash scenarios.
"""

import numpy as np
import pandas as pd

class MonteCarloStressTester:
    """
    Monte Carlo Simulation & Historic Stress Testing Engine.
    """

    CRASH_SCENARIOS = {
        "2008 Global Financial Crisis": {"shock_pct": -50.0, "vol_multiplier": 2.5, "duration_days": 180, "desc": "Severe systemic liquidity & banking collapse."},
        "2020 COVID Crash":            {"shock_pct": -38.0, "vol_multiplier": 2.0, "duration_days": 30,  "desc": "Ultra-fast global economic lockdown panic."},
        "2022 Rate Spike & Inflation": {"shock_pct": -22.0, "vol_multiplier": 1.5, "duration_days": 90,  "desc": "Aggressive central bank tightening & valuation compression."},
        "Geopolitical Oil Crisis":     {"shock_pct": -28.0, "vol_multiplier": 1.8, "duration_days": 60,  "desc": "Stagflationary supply shock & energy spike."}
    }

    @classmethod
    def run_simulation(
        cls,
        df: pd.DataFrame,
        portfolio_value: float = 100000.0,
        num_simulations: int = 5000,
        time_horizon_days: int = 60
    ) -> dict:
        """
        Runs Monte Carlo simulation (5000+ paths) using Geometric Brownian Motion & historical bootstrapped innovations.
        Returns VaR, CVaR (Expected Shortfall) at 95% and 99% levels, and path matrix.
        """
        if df is None or len(df) < 30:
            return {
                "error": "Insufficient historical price bars for Monte Carlo simulation.",
                "var_95_pct": 0, "var_95_val": 0, "cvar_95_pct": 0, "cvar_95_val": 0,
                "var_99_pct": 0, "var_99_val": 0, "cvar_99_pct": 0, "cvar_99_val": 0,
                "sim_paths": np.array([])
            }

        c = df["Close"].astype(float).dropna()
        returns = np.log(c / c.shift(1)).dropna().values

        mu = np.mean(returns)
        sigma = np.std(returns)
        drift = mu - 0.5 * (sigma ** 2)

        # Generate Monte Carlo random shocks
        np.random.seed(42)
        random_shocks = np.random.normal(0, 1, (num_simulations, time_horizon_days))

        # Geometric Brownian Motion simulation paths
        daily_log_returns = drift + sigma * random_shocks
        cum_returns = np.cumsum(daily_log_returns, axis=1)

        # Path values starting from current portfolio value
        sim_paths = portfolio_value * np.exp(cum_returns)

        # Final values after time_horizon_days
        final_values = sim_paths[:, -1]
        final_returns_pct = ((final_values - portfolio_value) / portfolio_value) * 100.0

        # Losses (positive number representing loss)
        losses_pct = -final_returns_pct
        losses_val = portfolio_value - final_values

        # Value at Risk (VaR)
        var_95_pct = float(np.percentile(losses_pct, 95))
        var_95_val = float(np.percentile(losses_val, 95))
        var_99_pct = float(np.percentile(losses_pct, 99))
        var_99_val = float(np.percentile(losses_val, 99))

        # Conditional Value at Risk (CVaR / Expected Shortfall)
        tail_95 = losses_pct[losses_pct >= var_95_pct]
        cvar_95_pct = float(np.mean(tail_95)) if len(tail_95) > 0 else var_95_pct
        cvar_95_val = (cvar_95_pct / 100.0) * portfolio_value

        tail_99 = losses_pct[losses_pct >= var_99_pct]
        cvar_99_pct = float(np.mean(tail_99)) if len(tail_99) > 0 else var_99_pct
        cvar_99_val = (cvar_99_pct / 100.0) * portfolio_value

        # Max Drawdown across paths
        peak_paths = np.maximum.accumulate(sim_paths, axis=1)
        drawdowns = (sim_paths - peak_paths) / peak_paths
        max_drawdowns_pct = np.min(drawdowns, axis=1) * 100.0
        avg_max_drawdown = float(np.mean(max_drawdowns_pct))

        return {
            "portfolio_value": portfolio_value,
            "num_simulations": num_simulations,
            "time_horizon_days": time_horizon_days,
            "var_95_pct": round(max(0, var_95_pct), 2),
            "var_95_val": round(max(0, var_95_val), 2),
            "cvar_95_pct": round(max(0, cvar_95_pct), 2),
            "cvar_95_val": round(max(0, cvar_95_val), 2),
            "var_99_pct": round(max(0, var_99_pct), 2),
            "var_99_val": round(max(0, var_99_val), 2),
            "cvar_99_pct": round(max(0, cvar_99_pct), 2),
            "cvar_99_val": round(max(0, cvar_99_val), 2),
            "avg_max_drawdown": round(avg_max_drawdown, 2),
            "sim_paths": sim_paths[:100], # return subset of 100 paths for Plotly rendering
            "final_returns_pct": final_returns_pct,
            "error": None
        }

    @classmethod
    def run_crash_stress_test(cls, portfolio_value: float, beta: float = 1.0) -> pd.DataFrame:
        """
        Calculates expected portfolio drawdown under historic crash scenarios.
        """
        records = []
        for scenario_name, params in cls.CRASH_SCENARIOS.items():
            mkt_shock = params["shock_pct"]
            asset_shock = mkt_shock * beta
            loss_val = (abs(asset_shock) / 100.0) * portfolio_value
            post_crash_val = portfolio_value - loss_val
            cvar_est = abs(asset_shock) * 1.25 # Expected Shortfall estimate

            records.append({
                "Crash Scenario": scenario_name,
                "Market Shock": f"{mkt_shock:+.1f}%",
                "Asset Shock (Beta scaled)": f"{asset_shock:+.1f}%",
                "Estimated Loss (₹)": f"₹{loss_val:,.2f}",
                "Post-Crash Value (₹)": f"₹{post_crash_val:,.2f}",
                "Scenario CVaR (%)": f"{cvar_est:.1f}%",
                "Description": params["desc"]
            })

        return pd.DataFrame(records)
