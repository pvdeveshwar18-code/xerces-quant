import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.holtwinters import ExponentialSmoothing

MIN_OBS = 60
DEFAULT_HOLDOUT = 60

# Lazy imports for ML models
def _get_ml_models():
    has_sklearn = False
    has_xgboost = False
    try:
        from sklearn.ensemble import RandomForestRegressor
        has_sklearn = True
    except ImportError:
        pass
    try:
        from xgboost import XGBRegressor
        has_xgboost = True
    except ImportError:
        pass
    return has_sklearn, has_xgboost

def _clean_series(series: pd.Series) -> pd.Series:
    s = series.astype(float).replace([np.inf, -np.inf], np.nan).dropna()
    return s[s > 0]

def _mape(actual: np.ndarray, predicted: np.ndarray) -> float | None:
    if len(actual) < 2 or len(predicted) < 2:
        return None
    n = min(len(actual), len(predicted))
    actual = actual[:n]
    predicted = predicted[:n]
    denom = np.maximum(np.abs(actual), 1e-9)
    return float(np.mean(np.abs((actual - predicted) / denom)) * 100)

def _directional_accuracy(actual: np.ndarray, predicted: np.ndarray) -> float | None:
    if len(actual) < 3 or len(predicted) < 3:
        return None
    n = min(len(actual), len(predicted))
    actual = actual[:n]
    predicted = predicted[:n]
    act_dir = np.sign(np.diff(actual))
    pred_dir = np.sign(np.diff(predicted))
    return float(np.mean(act_dir == pred_dir) * 100)

def naive_forecast(series: pd.Series, steps: int) -> pd.Series:
    s = _clean_series(series)
    if len(s) < 2:
        last = float(s.iloc[-1]) if len(s) else 0.0
        return pd.Series([last] * steps)
    drift = (float(s.iloc[-1]) - float(s.iloc[-min(20, len(s))])) / max(min(20, len(s) - 1), 1)
    vals = [float(s.iloc[-1]) + drift * i for i in range(1, steps + 1)]
    return pd.Series(vals)

def run_arima(series: pd.Series, steps: int = 260, max_p: int = 3, max_q: int = 3):
    log_s = np.log(_clean_series(series))
    if len(log_s) < MIN_OBS:
        raise ValueError(f"Need at least {MIN_OBS} observations for ARIMA")

    try:
        d = 0 if adfuller(log_s)[1] < 0.05 else 1
    except Exception:
        d = 1

    best_aic, best_model, best_order = np.inf, None, (1, d, 1)
    # Reduced grid search for speed on streamlit reruns
    for p in range(0, max_p + 1):
        for q in range(0, max_q + 1):
            if p == 0 and q == 0:
                continue
            try:
                m = ARIMA(log_s, order=(p, d, q)).fit()
                if m.aic < best_aic:
                    best_aic, best_model, best_order = m.aic, m, (p, d, q)
            except Exception:
                continue

    if best_model is None:
        best_model = ARIMA(log_s, order=(1, d, 1)).fit()
        best_order = (1, d, 1)
        best_aic = best_model.aic

    fc = best_model.get_forecast(steps=steps)
    mu = fc.predicted_mean
    ci = fc.conf_int(alpha=0.10)
    return (
        np.exp(mu),
        np.exp(ci.iloc[:, 0]),
        np.exp(ci.iloc[:, 1]),
        best_order,
        round(float(best_aic), 1),
        best_model,
        log_s,
    )

def run_holt_winters(series: pd.Series, steps: int = 260) -> pd.Series:
    s = _clean_series(series)
    if len(s) < MIN_OBS:
        return naive_forecast(s, steps)
    try:
        model = ExponentialSmoothing(
            s,
            trend="add",
            damped_trend=True,
            seasonal=None,
            initialization_method="estimated",
        ).fit(optimized=True)
        return model.forecast(steps=steps)
    except Exception:
        try:
            model = ExponentialSmoothing(
                s, trend="add", seasonal=None, initialization_method="estimated"
            ).fit()
            return model.forecast(steps=steps)
        except Exception:
            return naive_forecast(s, steps)

# ── UPGRADED ENSEMBLE FORECASTS (Random Forest & XGBoost) ──
def fit_ml_forecast(series: pd.Series, steps: int, model_type: str = "rf") -> pd.Series:
    """
    Fits an ML regressor (RandomForest or XGBoost) on lagged price values.
    Recursively forecasts step-by-step.
    """
    s = _clean_series(series)
    if len(s) < MIN_OBS:
        return naive_forecast(s, steps)
        
    has_sklearn, has_xgboost = _get_ml_models()
    
    # Check if requested package is available
    if model_type == "rf" and not has_sklearn:
        # Fallback to linear-trend + seasonality regressor
        return fit_seasonality_regression(s, steps)
    if model_type == "xgb" and not has_xgboost:
        # Fallback to naive forecast with random drift
        return naive_forecast(s, steps)

    # Prepare lag features
    lags = 5
    X, y = [], []
    vals = s.values
    for i in range(lags, len(vals)):
        X.append(vals[i-lags:i])
        y.append(vals[i])
    X, y = np.array(X), np.array(y)

    # Train model
    if model_type == "rf":
        from sklearn.ensemble import RandomForestRegressor
        model = RandomForestRegressor(n_estimators=50, max_depth=6, random_state=42)
    else:
        from xgboost import XGBRegressor
        model = XGBRegressor(n_estimators=50, max_depth=4, learning_rate=0.1, random_state=42)
        
    model.fit(X, y)

    # Recursive forecasting
    fc = list(vals[-lags:])
    fc_out = []
    for _ in range(steps):
        pred_input = np.array([fc[-lags:]])
        pred = float(model.predict(pred_input)[0])
        fc_out.append(pred)
        fc.append(pred)
        
    return pd.Series(fc_out, index=pd.RangeIndex(start=len(s), stop=len(s)+steps))

def fit_seasonality_regression(series: pd.Series, steps: int) -> pd.Series:
    """
    Custom lightweight regressor capturing trend + seasonality (Fourier terms).
    Serves as our 'Prophet' surrogate when prophet is not installed.
    """
    s = _clean_series(series)
    n = len(s)
    t = np.arange(n)
    
    # Fourier terms for weekly/monthly seasonality
    f1 = np.sin(2 * np.pi * t / 5.0)
    f2 = np.cos(2 * np.pi * t / 5.0)
    f3 = np.sin(2 * np.pi * t / 20.0)
    f4 = np.cos(2 * np.pi * t / 20.0)
    
    X = np.column_stack([np.ones(n), t, f1, f2, f3, f4])
    y = s.values
    
    # Solve OLS
    try:
        beta = np.linalg.lstsq(X, y, rcond=None)[0]
    except Exception:
        return naive_forecast(s, steps)
        
    # Predict future steps
    t_fut = np.arange(n, n + steps)
    f1_fut = np.sin(2 * np.pi * t_fut / 5.0)
    f2_fut = np.cos(2 * np.pi * t_fut / 5.0)
    f3_fut = np.sin(2 * np.pi * t_fut / 20.0)
    f4_fut = np.cos(2 * np.pi * t_fut / 20.0)
    
    X_fut = np.column_stack([np.ones(steps), t_fut, f1_fut, f2_fut, f3_fut, f4_fut])
    fc = np.dot(X_fut, beta)
    
    # Cap to avoid negative prices or extreme spikes
    last_val = y[-1]
    fc = np.clip(fc, last_val * 0.5, last_val * 2.0)
    
    return pd.Series(fc)

def _holdout_forecasts(train: pd.Series, holdout: int):
    """Generate holdout predictions for ARIMA, HW/ETS, RF, XGB, and Naive."""
    arima_fc = hw_fc = rf_fc = xgb_fc = naive_fc = None
    arima_order = (1, 1, 1)

    try:
        m_arima, _, _, best_order, _, _, _ = run_arima(train, steps=holdout)
        arima_fc = m_arima.values
        arima_order = best_order
    except Exception:
        pass

    try:
        hw_fc = run_holt_winters(train, steps=holdout).values
    except Exception:
        pass

    try:
        rf_fc = fit_ml_forecast(train, steps=holdout, model_type="rf").values
    except Exception:
        pass

    try:
        xgb_fc = fit_ml_forecast(train, steps=holdout, model_type="xgb").values
    except Exception:
        pass

    try:
        naive_fc = naive_forecast(train, steps=holdout).values
    except Exception:
        pass

    return arima_fc, hw_fc, rf_fc, xgb_fc, naive_fc, arima_order

def validate_models(price_series: pd.Series, holdout: int = DEFAULT_HOLDOUT) -> dict:
    """Backtest and validate forecasting models on a rolling holdout window."""
    s = _clean_series(price_series)
    if len(s) < holdout + MIN_OBS:
        return {
            "arima_mape": None, "hw_mape": None, "rf_mape": None, "xgb_mape": None, "naive_mape": None,
            "dir_acc": None, "arima_order": (1, 1, 1),
            "weights": {"arima": 0.2, "hw": 0.2, "rf": 0.2, "xgb": 0.2, "naive": 0.2},
            "edge_vs_naive": None, "best_model": "naive", "ensemble_mape": None
        }

    train = s.iloc[:-holdout]
    test = s.iloc[-holdout:].values
    arima_fc, hw_fc, rf_fc, xgb_fc, naive_fc, arima_order = _holdout_forecasts(train, holdout)

    metrics = {}
    models_list = [("arima", arima_fc), ("hw", hw_fc), ("rf", rf_fc), ("xgb", xgb_fc), ("naive", naive_fc)]
    
    for name, fc in models_list:
        if fc is not None and len(fc) >= 2:
            metrics[f"{name}_mape"] = _mape(test, fc)
            if name == "arima":
                metrics["dir_acc"] = _directional_accuracy(test, fc)
        else:
            metrics[f"{name}_mape"] = None

    if metrics.get("dir_acc") is None and hw_fc is not None:
        metrics["dir_acc"] = _directional_accuracy(test, hw_fc)

    # Inverse-MAPE weights (better models get higher weights)
    inv = {}
    for name, _ in models_list:
        mape = metrics.get(f"{name}_mape")
        inv[name] = 1.0 / max(mape, 0.5) if mape is not None else 0.0

    total = sum(inv.values()) or 1.0
    weights = {k: v / total for k, v in inv.items()}

    best_model = max(weights, key=weights.get)
    naive_mape = metrics.get("naive_mape")
    
    # Calculate ensemble prediction on holdout
    ensemble_fc_holdout = np.zeros(holdout)
    valid_count = 0
    for name, fc in models_list:
        if fc is not None:
            ensemble_fc_holdout += weights[name] * fc[:holdout]
            valid_count += 1
            
    ensemble_mape = _mape(test, ensemble_fc_holdout) if valid_count > 0 else None

    edge = None
    if naive_mape and ensemble_mape is not None and naive_mape > 0:
        edge = round((naive_mape - ensemble_mape) / naive_mape * 100, 1)

    metrics["arima_order"] = arima_order
    metrics["weights"] = weights
    metrics["edge_vs_naive"] = edge
    metrics["best_model"] = best_model
    metrics["ensemble_mape"] = ensemble_mape
    return metrics

def compute_forecast_bundle(price_series: pd.Series, steps: int, holdout: int = DEFAULT_HOLDOUT) -> dict:
    """
    Fit ARIMA, Holt-Winters, Random Forest, XGBoost, and Naive models.
    Validate on holdout, compute weights, and output the consensus ensemble.
    """
    s = _clean_series(price_series)
    validation = validate_models(s, holdout=holdout)

    fc_arima, fc_lo, fc_hi, arima_order, aic_val, arima_model, log_s = run_arima(s, steps)
    fc_hw = run_holt_winters(s, steps)
    fc_rf = fit_ml_forecast(s, steps, model_type="rf")
    fc_xgb = fit_ml_forecast(s, steps, model_type="xgb")
    fc_naive = naive_forecast(s, steps)

    w = validation["weights"]
    ensemble = (
        w["arima"] * fc_arima.values
        + w["hw"] * fc_hw.values
        + w["rf"] * fc_rf.values
        + w["xgb"] * fc_xgb.values
        + w["naive"] * fc_naive.values
    )

    return {
        "fc_arima": fc_arima,
        "fc_lo": fc_lo,
        "fc_hi": fc_hi,
        "fc_hw": fc_hw,
        "fc_rf": fc_rf,
        "fc_xgb": fc_xgb,
        "fc_naive": fc_naive,
        "fc_ensemble": pd.Series(ensemble),
        "arima_order": arima_order,
        "aic": aic_val,
        "arima_model": arima_model,
        "log_series": log_s,
        "target_arima": float(fc_arima.iloc[-1]),
        "target_hw": float(fc_hw.iloc[-1]),
        "target_rf": float(fc_rf.iloc[-1]),
        "target_xgb": float(fc_xgb.iloc[-1]),
        "target_naive": float(fc_naive.iloc[-1]),
        "target_ensemble": float(ensemble[-1]),
        "validation": validation,
        "weights": w,
        "arima_mape": validation.get("arima_mape"),
        "hw_mape": validation.get("hw_mape"),
        "rf_mape": validation.get("rf_mape"),
        "xgb_mape": validation.get("xgb_mape"),
        "naive_mape": validation.get("naive_mape"),
        "ensemble_mape": validation.get("ensemble_mape"),
        "dir_acc": validation.get("dir_acc"),
        "edge_vs_naive": validation.get("edge_vs_naive"),
        "best_model": validation.get("best_model"),
    }
