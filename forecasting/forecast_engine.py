"""
XERCES GARCH Volatility & Multi-Model Forecast Engine
Combines GARCH(1,1) heteroskedasticity modeling with ARIMA, Holt-Winters ETS, and Momentum Drift.
"""

import numpy as np
import pandas as pd
from scipy.optimize import minimize
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.holtwinters import ExponentialSmoothing

class GARCHVolatilityModel:
    """
    GARCH(1, 1) Volatility Model: sigma_t^2 = omega + alpha * epsilon_{t-1}^2 + beta * sigma_{t-1}^2
    """

    @classmethod
    def fit_and_forecast(cls, log_returns: pd.Series, forecast_horizon: int = 30) -> dict:
        """
        Fits GARCH(1, 1) model via Maximum Likelihood Estimation and forecasts volatility.
        """
        r = log_returns.dropna().values
        if len(r) < 30:
            vol_stat = float(np.std(r) * np.sqrt(252)) if len(r) > 5 else 0.20
            return {
                "annualized_vol": round(vol_stat * 100, 2),
                "garch_vol_series": np.full(forecast_horizon, vol_stat / np.sqrt(252)),
                "persistence": 0.95,
                "omega": 0.00001,
                "alpha": 0.05,
                "beta": 0.90
            }

        # Demean returns
        returns = r - np.mean(r)
        initial_var = np.var(returns)

        # GARCH Likelihood function
        def garch_log_likelihood(params):
            omega, alpha, beta = params
            if omega <= 0 or alpha < 0 or beta < 0 or (alpha + beta) >= 1.0:
                return 1e10
            
            n = len(returns)
            sigma2 = np.zeros(n)
            sigma2[0] = initial_var
            for t in range(1, n):
                sigma2[t] = omega + alpha * (returns[t-1]**2) + beta * sigma2[t-1]
            
            # Negative log likelihood under Gaussian assumption
            log_lik = -0.5 * np.sum(np.log(sigma2) + (returns**2) / sigma2)
            return -log_lik

        # Initial guess & bounds
        init_params = [0.05 * initial_var, 0.08, 0.90]
        bounds = [(1e-8, None), (1e-6, 0.4), (1e-6, 0.98)]

        try:
            res = minimize(garch_log_likelihood, init_params, method='L-BFGS-B', bounds=bounds)
            omega, alpha, beta = res.x
        except Exception:
            omega, alpha, beta = 0.05 * initial_var, 0.08, 0.88

        # Current conditional variance
        last_ret = returns[-1]
        last_var = initial_var
        for t in range(1, len(returns)):
            last_var = omega + alpha * (returns[t-1]**2) + beta * last_var

        # Forecast h-step ahead conditional variance: sigma_{t+h}^2 = VL + (alpha+beta)^h * (sigma_t^2 - VL)
        persistence = alpha + beta
        long_run_var = omega / (1.0 - persistence + 1e-8)

        forecast_vars = np.zeros(forecast_horizon)
        current_v = last_var
        for h in range(forecast_horizon):
            current_v = omega + persistence * current_v
            forecast_vars[h] = current_v

        forecast_vols = np.sqrt(forecast_vars)
        annualized_current_vol = np.sqrt(last_var * 252) * 100.0

        return {
            "annualized_vol": round(float(annualized_current_vol), 2),
            "garch_vol_series": forecast_vols,
            "persistence": round(float(persistence), 4),
            "omega": float(omega),
            "alpha": float(alpha),
            "beta": float(beta)
        }


class MultiModelForecastEngine:
    """
    Combines GARCH Volatility, ARIMA, Holt-Winters (ETS), and Drift models into a unified forecast.
    """

    @classmethod
    def forecast_consensus(cls, df: pd.DataFrame, forecast_days: int = 30) -> dict:
        if df is None or len(df) < 50:
            return {
                "error": "Insufficient historical data for forecasting (minimum 50 bars needed).",
                "forecast_df": pd.DataFrame(),
                "metrics": {}
            }

        close = df['Close'].astype(float).dropna()
        last_date = df['Date'].iloc[-1] if 'Date' in df.columns else df.index[-1]
        future_dates = pd.date_range(start=pd.to_datetime(last_date) + pd.Timedelta(days=1), periods=forecast_days, freq='B')
        last_price = float(close.iloc[-1])

        # Log returns for GARCH
        log_ret = np.log(close / close.shift(1)).dropna()

        # 1. GARCH Volatility Estimation
        garch_res = GARCHVolatilityModel.fit_and_forecast(log_ret, forecast_horizon=forecast_days)
        garch_vols = garch_res["garch_vol_series"]

        # 2. ARIMA Model
        try:
            log_close = np.log(close.values)
            arima_mod = ARIMA(log_close, order=(2, 1, 2)).fit()
            arima_log_pred = arima_mod.forecast(steps=forecast_days)
            arima_pred = np.exp(arima_log_pred)
        except Exception:
            try:
                arima_mod = ARIMA(close.values, order=(1, 1, 1)).fit()
                arima_pred = arima_mod.forecast(steps=forecast_days)
            except Exception:
                arima_pred = np.full(forecast_days, last_price)

        # 3. Holt-Winters Exponential Smoothing
        try:
            ets_mod = ExponentialSmoothing(close.values, trend='add', seasonal=None, initialization_method="estimated").fit()
            ets_pred = ets_mod.forecast(forecast_days)
        except Exception:
            ets_pred = np.full(forecast_days, last_price)

        # 4. Linear Momentum Drift
        ret_20 = close.pct_change(20).dropna()
        drift_rate = ret_20.mean() / 20.0 if len(ret_20) > 0 else 0.0
        drift_pred = np.array([last_price * ((1 + drift_rate) ** i) for i in range(1, forecast_days + 1)])

        # 5. Weighted Multi-Model Ensemble
        # Weights: ARIMA 40%, Holt-Winters 40%, Drift 20%
        consensus = (0.40 * arima_pred) + (0.40 * ets_pred) + (0.20 * drift_pred)

        # Dynamic GARCH-scaled Confidence Intervals (95% & 99%)
        cum_garch_sigma = np.sqrt(np.cumsum(garch_vols**2)) * last_price
        upper_95 = consensus + (1.96 * cum_garch_sigma)
        lower_95 = np.maximum(0.1, consensus - (1.96 * cum_garch_sigma))
        upper_99 = consensus + (2.58 * cum_garch_sigma)
        lower_99 = np.maximum(0.1, consensus - (2.58 * cum_garch_sigma))

        forecast_df = pd.DataFrame({
            'Consensus_Forecast': consensus,
            'ARIMA_Forecast': arima_pred,
            'ETS_Forecast': ets_pred,
            'Drift_Forecast': drift_pred,
            'GARCH_Vol_Annualized': garch_res["annualized_vol"],
            'Upper_95': upper_95,
            'Lower_95': lower_95,
            'Upper_99': upper_99,
            'Lower_99': lower_99
        }, index=future_dates)

        target = float(consensus[-1])
        pct_chg = float(((target / last_price) - 1.0) * 100.0)
        direction = "BULLISH" if pct_chg > 1.5 else ("BEARISH" if pct_chg < -1.5 else "NEUTRAL")

        return {
            "last_price": round(last_price, 2),
            "forecast_target": round(target, 2),
            "forecast_pct_change": round(pct_chg, 2),
            "directional_bias": direction,
            "garch_annualized_vol": garch_res["annualized_vol"],
            "garch_persistence": garch_res["persistence"],
            "upper_95": round(float(upper_95[-1]), 2),
            "lower_95": round(float(lower_95[-1]), 2),
            "upper_99": round(float(upper_99[-1]), 2),
            "lower_99": round(float(lower_99[-1]), 2),
            "forecast_df": forecast_df,
            "error": None
        }
