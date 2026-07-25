"""
XERCES Institutional Risk Engine
Calculates VaR, CVaR, Kelly Criterion, Maximum Drawdown, ATR stops, and Volatility metrics.
"""

import numpy as np
import pandas as pd
from scipy.stats import norm

class InstitutionalRiskEngine:
    """
    Comprehensive risk metrics calculator for single assets and portfolios.
    """

    @staticmethod
    def calculate_risk_metrics(df: pd.DataFrame, portfolio_value: float = 500000.0, confidence_level: float = 0.95) -> dict:
        """
        Calculates VaR, CVaR, Kelly Criterion, Max Drawdown, and volatility statistics.
        """
        if df is None or len(df) < 30:
            return {
                "var_95_pct": 0.0,
                "var_95_amount": 0.0,
                "cvar_95_pct": 0.0,
                "cvar_95_amount": 0.0,
                "max_drawdown_pct": 0.0,
                "kelly_fraction": 0.0,
                "sharpe_ratio": 0.0,
                "sortino_ratio": 0.0,
                "annualized_volatility": 0.0,
                "atr_14": 0.0,
                "recommended_stop_loss": 0.0
            }

        close = df['Close']
        returns = close.pct_change().dropna()
        latest_price = close.iloc[-1]

        # 1. Annualized Volatility
        daily_vol = returns.std()
        annualized_vol = daily_vol * np.sqrt(252) * 100

        # 2. Value at Risk (VaR) & CVaR (Historical & Parametric)
        # 1-day Parametric VaR
        z_score = norm.ppf(confidence_level)
        var_param_pct = (z_score * daily_vol) * 100
        var_param_amount = portfolio_value * (var_param_pct / 100.0)

        # 1-day Historical VaR & CVaR (Expected Shortfall)
        var_hist_pct = -np.percentile(returns, (1 - confidence_level) * 100) * 100
        cvar_hist_returns = returns[returns <= - (var_hist_pct / 100.0)]
        cvar_hist_pct = -cvar_hist_returns.mean() * 100 if len(cvar_hist_returns) > 0 else var_hist_pct * 1.3
        cvar_amount = portfolio_value * (cvar_hist_pct / 100.0)

        # 3. Maximum Drawdown
        cum_returns = (1 + returns).cumprod()
        rolling_max = cum_returns.cummax()
        drawdowns = (cum_returns - rolling_max) / rolling_max
        max_dd_pct = abs(drawdowns.min()) * 100

        # 4. Sharpe & Sortino Ratios (Assumes 6.5% Risk Free Rate for India RBI)
        rf_daily = 0.065 / 252
        excess_returns = returns - rf_daily
        sharpe = (excess_returns.mean() / (daily_vol + 1e-8)) * np.sqrt(252)

        downside_returns = returns[returns < 0]
        downside_std = downside_returns.std() if len(downside_returns) > 0 else daily_vol
        sortino = (excess_returns.mean() / (downside_std + 1e-8)) * np.sqrt(252)

        # 5. Kelly Criterion calculation
        # Win Rate (W) and Win/Loss Ratio (R)
        positive_returns = returns[returns > 0]
        negative_returns = returns[returns < 0]

        win_rate = len(positive_returns) / len(returns) if len(returns) > 0 else 0.5
        avg_win = positive_returns.mean() if len(positive_returns) > 0 else 0.01
        avg_loss = abs(negative_returns.mean()) if len(negative_returns) > 0 else 0.01

        win_loss_ratio = avg_win / avg_loss if avg_loss > 0 else 1.0

        # Full Kelly Formula: K% = W - [(1 - W) / R]
        kelly_full = win_rate - ((1 - win_rate) / win_loss_ratio)
        # Fractional Kelly (Half Kelly for conservative risk management)
        half_kelly = max(0.0, min(kelly_full * 0.5, 0.25))

        # 6. ATR Stop Loss Level
        if 'High' in df.columns and 'Low' in df.columns:
            tr1 = df['High'] - df['Low']
            tr2 = (df['High'] - close.shift(1)).abs()
            tr3 = (df['Low'] - close.shift(1)).abs()
            tr = pd.concat([tr1, tr2, tr3], axis=1).max(axis=1)
            atr_14 = tr.rolling(14).mean().iloc[-1]
        else:
            atr_14 = latest_price * 0.02

        rec_stop_loss = latest_price - (2.0 * atr_14)

        return {
            "var_95_pct": round(float(var_param_pct), 2),
            "var_95_amount": round(float(var_param_amount), 2),
            "cvar_95_pct": round(float(cvar_hist_pct), 2),
            "cvar_95_amount": round(float(cvar_amount), 2),
            "max_drawdown_pct": round(float(max_dd_pct), 2),
            "kelly_fraction": round(float(half_kelly), 4),
            "kelly_pct": round(float(half_kelly * 100), 2),
            "win_rate_pct": round(float(win_rate * 100), 2),
            "win_loss_ratio": round(float(win_loss_ratio), 2),
            "sharpe_ratio": round(float(sharpe), 2),
            "sortino_ratio": round(float(sortino), 2),
            "annualized_volatility": round(float(annualized_vol), 2),
            "atr_14": round(float(atr_14), 2),
            "recommended_stop_loss": round(float(rec_stop_loss), 2)
        }
