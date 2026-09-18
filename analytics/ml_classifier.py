import numpy as np
import pandas as pd

def prepare_ml_features(df: pd.DataFrame) -> pd.DataFrame:
    """Extract quantitative features for machine learning classification."""
    feat = pd.DataFrame(index=df.index)
    close = df["Close"].astype(float)

    feat["RSI_14"] = df["RSI_14"].astype(float) if "RSI_14" in df.columns else 50.0
    feat["MACD"] = df["MACD"].astype(float) if "MACD" in df.columns else 0.0
    feat["MACD_Signal"] = df["MACD_Signal"].astype(float) if "MACD_Signal" in df.columns else 0.0
    feat["MACD_Hist"] = df["MACD_Hist"].astype(float) if "MACD_Hist" in df.columns else 0.0

    if "SMA_20" in df.columns:
        feat["SMA_20_ratio"] = (close / df["SMA_20"].astype(float)) - 1.0
    else:
        feat["SMA_20_ratio"] = 0.0

    if "SMA_50" in df.columns:
        feat["SMA_50_ratio"] = (close / df["SMA_50"].astype(float)) - 1.0
    else:
        feat["SMA_50_ratio"] = 0.0

    if "SMA_200" in df.columns:
        feat["SMA_200_ratio"] = (close / df["SMA_200"].astype(float)) - 1.0
    else:
        feat["SMA_200_ratio"] = 0.0

    if "BB_Upper" in df.columns and "BB_Lower" in df.columns:
        bb_upper = df["BB_Upper"].astype(float)
        bb_lower = df["BB_Lower"].astype(float)
        bbrange = np.maximum(bb_upper - bb_lower, 1e-9)
        feat["BB_Pct"] = (close - bb_lower) / bbrange
    else:
        feat["BB_Pct"] = 0.5

    if "ATR_14" in df.columns:
        feat["ATR_Pct"] = df["ATR_14"].astype(float) / (close + 1e-9)
    else:
        feat["ATR_Pct"] = 0.02

    if "Volume" in df.columns:
        vol = df["Volume"].astype(float)
        vol_ma = vol.rolling(20).mean() + 1e-9
        feat["Vol_Ratio"] = (vol / vol_ma) - 1.0
    else:
        feat["Vol_Ratio"] = 0.0

    feat["Mom_5d"] = close.pct_change(5)
    feat["Mom_10d"] = close.pct_change(10)
    feat["Volatility_20"] = df["Volatility_20"].astype(float) if "Volatility_20" in df.columns else 0.2

    return feat.fillna(0.0)

def train_and_predict_ml_signal(df: pd.DataFrame) -> dict:
    """
    Train Random Forest classifier on historical price features and predict current market directional probability.
    Returns signal, probability breakdown, confidence score, and feature importances.
    """
    if len(df) < 100:
        return {
            "ml_signal": "HOLD",
            "confidence": 50.0,
            "prob_bull": 33.3,
            "prob_bear": 33.3,
            "prob_neutral": 33.4,
            "feature_importance": {},
            "status": "Insufficient data (minimum 100 bars required)"
        }

    features = prepare_ml_features(df)
    close = df["Close"].astype(float)

    # 5-day forward return as target label
    fwd_ret = (close.shift(-5) - close) / close

    # Labels: 1 (Bullish > +1.5%), -1 (Bearish < -1.5%), 0 (Neutral)
    labels = pd.Series(0, index=df.index)
    labels[fwd_ret > 0.015] = 1
    labels[fwd_ret < -0.015] = -1

    # Drop last 5 rows where target label is NaN
    valid_idx = features.index[:-5]
    X_train = features.loc[valid_idx]
    y_train = labels.loc[valid_idx]
    X_latest = features.iloc[[-1]]

    try:
        from sklearn.ensemble import RandomForestClassifier

        clf = RandomForestClassifier(
            n_estimators=120,
            max_depth=5,
            min_samples_split=5,
            random_state=42,
            class_weight="balanced"
        )
        clf.fit(X_train, y_train)

        probs = clf.predict_proba(X_latest)[0]
        classes = list(clf.classes_)

        prob_map = {c: p for c, p in zip(classes, probs)}
        prob_bull = round(float(prob_map.get(1, 0.0)) * 100, 1)
        prob_bear = round(float(prob_map.get(-1, 0.0)) * 100, 1)
        prob_neutral = round(float(prob_map.get(0, 0.0)) * 100, 1)

        if prob_bull > prob_bear and prob_bull >= 45.0:
            signal = "BUY"
            confidence = prob_bull
        elif prob_bear > prob_bull and prob_bear >= 45.0:
            signal = "SELL"
            confidence = prob_bear
        else:
            signal = "HOLD"
            confidence = prob_neutral

        # Feature importances
        imp_dict = {}
        for fname, imp in zip(features.columns, clf.feature_importances_):
            imp_dict[fname] = round(float(imp) * 100, 1)
        sorted_imp = dict(sorted(imp_dict.items(), key=lambda x: x[1], reverse=True)[:5])

        return {
            "ml_signal": signal,
            "confidence": round(confidence, 1),
            "prob_bull": prob_bull,
            "prob_bear": prob_bear,
            "prob_neutral": prob_neutral,
            "feature_importance": sorted_imp,
            "status": "Success"
        }

    except Exception as e:
        return {
            "ml_signal": "HOLD",
            "confidence": 50.0,
            "prob_bull": 33.3,
            "prob_bear": 33.3,
            "prob_neutral": 33.4,
            "feature_importance": {},
            "status": f"Error fitting model: {e}"
        }
