"""
XERCES forecast engine — defensive ARIMA / Holt-Winters / naive baseline
with holdout validation and validation-weighted ensemble.
"""

from __future__ import annotations

import numpy as np
import pandas as pd
from statsmodels.tsa.arima.model import ARIMA
from statsmodels.tsa.stattools import adfuller
from statsmodels.tsa.holtwinters import ExponentialSmoothing

MIN_OBS = 60
DEFAULT_HOLDOUT = 60
ARIMA_GRID = range(0, 4)  # smaller grid for speed on reruns
MODEL_NAMES = ("arima", "hw", "naive")


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


def _rmse_pct(actual: np.ndarray, predicted: np.ndarray) -> float | None:
    if len(actual) < 2 or len(predicted) < 2:
        return None
    n = min(len(actual), len(predicted))
    actual = actual[:n]
    predicted = predicted[:n]
    denom = np.maximum(np.abs(actual), 1e-9)
    return float(np.sqrt(np.mean(((actual - predicted) / denom) ** 2)) * 100)


def _safe_mean(values: list[float | None]) -> float | None:
    clean = [float(v) for v in values if v is not None and np.isfinite(v)]
    return float(np.mean(clean)) if clean else None


def _safe_std(values: list[float | None]) -> float | None:
    clean = [float(v) for v in values if v is not None and np.isfinite(v)]
    return float(np.std(clean, ddof=0)) if len(clean) > 1 else 0.0 if clean else None


def _renormalized_ensemble(forecasts: dict[str, np.ndarray | None], weights: dict[str, float], steps: int) -> np.ndarray | None:
    available = {name: fc for name, fc in forecasts.items() if fc is not None and len(fc) >= steps}
    if not available:
        return None
    weight_total = sum(weights.get(name, 0.0) for name in available) or 1.0
    out = np.zeros(steps)
    for name, fc in available.items():
        out += (weights.get(name, 0.0) / weight_total) * fc[:steps]
    return out


def _quality_summary(validation: dict, *, observations: int, steps: int, holdout: int) -> tuple[int, str, list[str]]:
    ensemble_mape = validation.get("ensemble_mape")
    dir_acc = validation.get("dir_acc")
    edge = validation.get("edge_vs_naive")
    valid_windows = int(validation.get("valid_windows", 0) or 0)
    mape_cv = float(validation.get("ensemble_mape_cv") or 1.0)

    notes = []
    score = 0.0

    if ensemble_mape is None:
        score += 12
        notes.append("No reliable holdout validation yet.")
    else:
        score += max(0.0, 35.0 * (1.0 - min(ensemble_mape, 20.0) / 20.0))
        if ensemble_mape > 12:
            notes.append("Forecast error is high on recent holdouts.")

    if edge is None:
        score += 4
        notes.append("Naive-baseline edge is not established.")
    else:
        score += max(0.0, min(20.0, (edge + 10.0) / 30.0 * 20.0))
        if edge <= 0:
            notes.append("Ensemble has not beaten the naive baseline recently.")

    if dir_acc is None:
        score += 5
    else:
        score += max(0.0, min(20.0, (dir_acc - 45.0) / 25.0 * 20.0))
        if dir_acc < 52:
            notes.append("Directional accuracy is close to coin-flip.")

    score += min(15.0, valid_windows * 5.0)
    if valid_windows < 3:
        notes.append("More validation windows would improve confidence.")

    stability_score = max(0.0, 10.0 * (1.0 - min(mape_cv, 1.0)))
    score += stability_score
    if mape_cv > 0.5:
        notes.append("Holdout error varies materially across windows.")

    score += min(10.0, observations / 504.0 * 10.0)

    if steps > holdout * 2:
        penalty = min(15.0, (steps / max(holdout, 1) - 2.0) * 2.0)
        score -= penalty
        notes.append("Forecast horizon extends beyond the validated holdout length.")

    score_i = int(max(0, min(100, round(score))))
    if score_i >= 85:
        label = "EXCELLENT"
    elif score_i >= 75:
        label = "STRONG"
    elif score_i >= 60:
        label = "MODERATE"
    elif score_i >= 45:
        label = "WEAK"
    else:
        label = "LOW"

    return score_i, label, notes[:5]


def _ensemble_prediction_band(ensemble: pd.Series, validation: dict, holdout: int) -> tuple[pd.Series, pd.Series]:
    p80 = validation.get("ensemble_abs_pct_error_p80")
    mape = validation.get("ensemble_mape")
    base_err = float(p80 or mape or 8.0) / 100.0
    base_err = max(0.02, min(base_err, 0.35))
    horizon_scale = np.sqrt(np.arange(1, len(ensemble) + 1) / max(holdout, 1))
    band_pct = np.maximum(base_err, base_err * horizon_scale)
    lo = np.maximum(ensemble.values * (1.0 - band_pct), 0.01)
    hi = ensemble.values * (1.0 + band_pct)
    return pd.Series(lo, index=ensemble.index), pd.Series(hi, index=ensemble.index)


def naive_forecast(series: pd.Series, steps: int) -> pd.Series:
    s = _clean_series(series)
    if len(s) < 2:
        last = float(s.iloc[-1]) if len(s) else 0.0
        return pd.Series([last] * steps)
    drift = (float(s.iloc[-1]) - float(s.iloc[-min(20, len(s))])) / max(min(20, len(s) - 1), 1)
    vals = [float(s.iloc[-1]) + drift * i for i in range(1, steps + 1)]
    return pd.Series(vals)


def run_arima(
    series: pd.Series,
    steps: int = 260,
    *,
    max_p: int = 3,
    max_q: int = 3,
):
    """Fit ARIMA on log-prices with a compact AIC grid. Returns price-level forecast."""
    log_s = np.log(_clean_series(series))
    if len(log_s) < MIN_OBS:
        raise ValueError(f"Need at least {MIN_OBS} observations for ARIMA")

    try:
        d = 0 if adfuller(log_s)[1] < 0.05 else 1
    except Exception:
        d = 1

    best_aic, best_model, best_order = np.inf, None, (1, d, 1)
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


def _holdout_forecasts(train: pd.Series, holdout: int):
    """One-step-ahead style holdout forecasts for each model."""
    log_train = np.log(_clean_series(train))
    arima_order = (1, 1, 1)
    arima_fc = hw_fc = naive_fc = None

    try:
        d = 0 if adfuller(log_train)[1] < 0.05 else 1
        best_aic, best_order = np.inf, (1, d, 1)
        for p in ARIMA_GRID:
            for q in ARIMA_GRID:
                if p == 0 and q == 0:
                    continue
                try:
                    m = ARIMA(log_train, order=(p, d, q)).fit()
                    if m.aic < best_aic:
                        best_aic, best_order = m.aic, (p, d, q)
                except Exception:
                    continue
        arima_order = best_order
        m = ARIMA(log_train, order=arima_order).fit()
        arima_fc = np.exp(m.forecast(steps=holdout).values)
    except Exception:
        pass

    try:
        hw_fc = run_holt_winters(train, holdout).values
    except Exception:
        pass

    try:
        naive_fc = naive_forecast(train, holdout).values
    except Exception:
        pass

    return arima_fc, hw_fc, naive_fc, arima_order


def validate_models(price_series: pd.Series, holdout: int = DEFAULT_HOLDOUT, windows: int = 3) -> dict:
    """Validate ARIMA, Holt-Winters, and naive across recent non-overlapping holdout windows."""
    s = _clean_series(price_series)
    if len(s) < holdout + MIN_OBS:
        validation = {
            "arima_mape": None,
            "hw_mape": None,
            "naive_mape": None,
            "arima_rmse_pct": None,
            "hw_rmse_pct": None,
            "naive_rmse_pct": None,
            "dir_acc": None,
            "arima_order": (1, 1, 1),
            "weights": {"arima": 1 / 3, "hw": 1 / 3, "naive": 1 / 3},
            "edge_vs_naive": None,
            "best_model": "naive",
            "ensemble_mape": None,
            "ensemble_rmse_pct": None,
            "ensemble_mape_std": None,
            "ensemble_mape_cv": None,
            "ensemble_abs_pct_error_p50": None,
            "ensemble_abs_pct_error_p80": None,
            "ensemble_abs_pct_error_p95": None,
            "validation_windows": [],
            "valid_windows": 0,
        }
        score, label, notes = _quality_summary(validation, observations=len(s), steps=holdout, holdout=holdout)
        validation.update({"quality_score": score, "quality_label": label, "quality_notes": notes})
        return validation

    max_windows = max(1, min(int(windows), (len(s) - MIN_OBS) // holdout))
    raw_windows = []
    arima_order = (1, 1, 1)
    model_mapes = {name: [] for name in MODEL_NAMES}
    model_rmse = {name: [] for name in MODEL_NAMES}
    model_dirs = {name: [] for name in MODEL_NAMES}

    for i in range(max_windows):
        test_end = len(s) - i * holdout
        test_start = test_end - holdout
        if test_start < MIN_OBS:
            continue

        train = s.iloc[:test_start]
        test = s.iloc[test_start:test_end].values
        if len(test) < 2:
            continue

        arima_fc, hw_fc, naive_fc, window_arima_order = _holdout_forecasts(train, len(test))
        if i == 0:
            arima_order = window_arima_order

        forecasts = {"arima": arima_fc, "hw": hw_fc, "naive": naive_fc}
        window_record = {
            "window": i + 1,
            "test_start": int(test_start),
            "test_end": int(test_end),
            "models": {},
        }

        for name, fc in forecasts.items():
            if fc is None or len(fc) < 2:
                window_record["models"][name] = {"mape": None, "rmse_pct": None, "dir_acc": None}
                continue
            mape = _mape(test, fc)
            rmse = _rmse_pct(test, fc)
            dacc = _directional_accuracy(test, fc)
            model_mapes[name].append(mape)
            model_rmse[name].append(rmse)
            model_dirs[name].append(dacc)
            window_record["models"][name] = {
                "mape": round(mape, 3) if mape is not None else None,
                "rmse_pct": round(rmse, 3) if rmse is not None else None,
                "dir_acc": round(dacc, 2) if dacc is not None else None,
            }

        raw_windows.append({"test": test, "forecasts": forecasts, "record": window_record})

    if not raw_windows:
        return validate_models(s.iloc[-(MIN_OBS + holdout - 1):], holdout=holdout, windows=1)

    penalized_errors = {}
    metrics = {}
    for name in MODEL_NAMES:
        mean_mape = _safe_mean(model_mapes[name])
        std_mape = _safe_std(model_mapes[name])
        mean_rmse = _safe_mean(model_rmse[name])
        mean_dir = _safe_mean(model_dirs[name])
        metrics[f"{name}_mape"] = mean_mape
        metrics[f"{name}_mape_std"] = std_mape
        metrics[f"{name}_rmse_pct"] = mean_rmse
        metrics[f"{name}_dir_acc"] = mean_dir
        if mean_mape is None:
            penalized_errors[name] = None
        else:
            cv = (std_mape or 0.0) / max(mean_mape, 1e-9)
            penalized_errors[name] = mean_mape * (1.0 + 0.25 * cv)

    inv = {
        name: (1.0 / max(err, 0.5) if err is not None else 0.0)
        for name, err in penalized_errors.items()
    }
    total = sum(inv.values())
    if total <= 0:
        weights = {name: 1.0 / len(MODEL_NAMES) for name in MODEL_NAMES}
    else:
        weights = {name: inv[name] / total for name in MODEL_NAMES}

    ensemble_mapes = []
    ensemble_rmse = []
    ensemble_dirs = []
    ensemble_abs_pct_errors = []
    validation_windows = []

    for item in raw_windows:
        test = item["test"]
        ens = _renormalized_ensemble(item["forecasts"], weights, len(test))
        rec = item["record"]
        if ens is not None:
            emape = _mape(test, ens)
            ermse = _rmse_pct(test, ens)
            edir = _directional_accuracy(test, ens)
            ensemble_mapes.append(emape)
            ensemble_rmse.append(ermse)
            ensemble_dirs.append(edir)
            pct_errors = np.abs((test[:len(ens)] - ens[:len(test)]) / np.maximum(np.abs(test[:len(ens)]), 1e-9)) * 100
            ensemble_abs_pct_errors.extend([float(x) for x in pct_errors if np.isfinite(x)])
            rec["ensemble"] = {
                "mape": round(emape, 3) if emape is not None else None,
                "rmse_pct": round(ermse, 3) if ermse is not None else None,
                "dir_acc": round(edir, 2) if edir is not None else None,
            }
        validation_windows.append(rec)

    ensemble_mape = _safe_mean(ensemble_mapes)
    ensemble_mape_std = _safe_std(ensemble_mapes)
    ensemble_mape_cv = (ensemble_mape_std or 0.0) / max(ensemble_mape or 0.0, 1e-9) if ensemble_mape else None
    ensemble_rmse_pct = _safe_mean(ensemble_rmse)
    dir_acc = _safe_mean(ensemble_dirs)
    naive_mape = metrics.get("naive_mape")

    edge = None
    if naive_mape and ensemble_mape is not None and naive_mape > 0:
        edge = round((naive_mape - ensemble_mape) / naive_mape * 100, 1)

    best_model = min(
        [name for name in MODEL_NAMES if metrics.get(f"{name}_mape") is not None],
        key=lambda name: metrics.get(f"{name}_mape"),
        default="naive",
    )

    if ensemble_abs_pct_errors:
        p50, p80, p95 = np.percentile(ensemble_abs_pct_errors, [50, 80, 95])
    else:
        p50 = p80 = p95 = None

    metrics.update({
        "arima_order": arima_order,
        "weights": weights,
        "edge_vs_naive": edge,
        "best_model": best_model,
        "ensemble_mape": ensemble_mape,
        "ensemble_rmse_pct": ensemble_rmse_pct,
        "ensemble_mape_std": ensemble_mape_std,
        "ensemble_mape_cv": ensemble_mape_cv,
        "ensemble_abs_pct_error_p50": float(p50) if p50 is not None else None,
        "ensemble_abs_pct_error_p80": float(p80) if p80 is not None else None,
        "ensemble_abs_pct_error_p95": float(p95) if p95 is not None else None,
        "dir_acc": dir_acc,
        "validation_windows": validation_windows,
        "valid_windows": len(validation_windows),
    })

    score, label, notes = _quality_summary(metrics, observations=len(s), steps=holdout, holdout=holdout)
    metrics.update({"quality_score": score, "quality_label": label, "quality_notes": notes})
    return metrics


def compute_forecast_bundle(price_series: pd.Series, steps: int, holdout: int = DEFAULT_HOLDOUT) -> dict:
    """
    Full forecast pipeline: fit models, validate, return weighted ensemble + diagnostics.
    """
    s = _clean_series(price_series)
    validation = validate_models(s, holdout=holdout)
    quality_score, quality_label, quality_notes = _quality_summary(
        validation, observations=len(s), steps=steps, holdout=holdout
    )
    validation.update({
        "quality_score": quality_score,
        "quality_label": quality_label,
        "quality_notes": quality_notes,
    })

    try:
        fc_mean, fc_lo, fc_hi, arima_order, aic_val, arima_model, log_s = run_arima(s, steps)
    except Exception:
        fc_mean = naive_forecast(s, steps)
        fc_lo = fc_mean * 0.95
        fc_hi = fc_mean * 1.05
        arima_order = (0, 0, 0)
        aic_val = None
        arima_model = None
        log_s = np.log(s)

    hw_series = run_holt_winters(s, steps)
    naive_series = naive_forecast(s, steps)

    w = validation["weights"]
    ensemble = (
        w["arima"] * fc_mean.values
        + w["hw"] * hw_series.values
        + w["naive"] * naive_series.values
    )

    target_arima = float(fc_mean.iloc[-1])
    target_hw = float(hw_series.iloc[-1])
    target_naive = float(naive_series.iloc[-1])
    target_ensemble = float(ensemble[-1])
    ensemble_series = pd.Series(ensemble)
    ensemble_lo, ensemble_hi = _ensemble_prediction_band(ensemble_series, validation, holdout)

    return {
        "fc_arima": fc_mean,
        "fc_lo": fc_lo,
        "fc_hi": fc_hi,
        "fc_hw": hw_series,
        "fc_naive": naive_series,
        "fc_ensemble": ensemble_series,
        "fc_ensemble_lo": ensemble_lo,
        "fc_ensemble_hi": ensemble_hi,
        "arima_order": arima_order,
        "aic": aic_val,
        "arima_model": arima_model,
        "log_series": log_s,
        "target_arima": target_arima,
        "target_hw": target_hw,
        "target_naive": target_naive,
        "target_ensemble": target_ensemble,
        "validation": validation,
        "weights": w,
        "arima_mape": validation.get("arima_mape"),
        "hw_mape": validation.get("hw_mape"),
        "naive_mape": validation.get("naive_mape"),
        "arima_rmse_pct": validation.get("arima_rmse_pct"),
        "hw_rmse_pct": validation.get("hw_rmse_pct"),
        "naive_rmse_pct": validation.get("naive_rmse_pct"),
        "ensemble_mape": validation.get("ensemble_mape"),
        "ensemble_rmse_pct": validation.get("ensemble_rmse_pct"),
        "ensemble_mape_std": validation.get("ensemble_mape_std"),
        "ensemble_mape_cv": validation.get("ensemble_mape_cv"),
        "ensemble_abs_pct_error_p50": validation.get("ensemble_abs_pct_error_p50"),
        "ensemble_abs_pct_error_p80": validation.get("ensemble_abs_pct_error_p80"),
        "ensemble_abs_pct_error_p95": validation.get("ensemble_abs_pct_error_p95"),
        "dir_acc": validation.get("dir_acc"),
        "edge_vs_naive": validation.get("edge_vs_naive"),
        "best_model": validation.get("best_model"),
        "valid_windows": validation.get("valid_windows"),
        "validation_windows": validation.get("validation_windows"),
        "quality_score": validation.get("quality_score"),
        "quality_label": validation.get("quality_label"),
        "quality_notes": validation.get("quality_notes"),
    }
