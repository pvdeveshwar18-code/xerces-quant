"""
XERCES ML Signal Classifier Module
Multi-Factor Machine Learning Model (Random Forest & XGBoost) with Model Persistence & AutoML Hyperparameter Tuning.
"""

import os
import joblib
import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from ai_committee.automl_tuner import AutoMLTuner

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False

MODEL_DIR = os.path.join(os.path.dirname(os.path.dirname(__file__)), "models")
os.makedirs(MODEL_DIR, exist_ok=True)
DEFAULT_MODEL_PATH = os.path.join(MODEL_DIR, "ml_signal_classifier.joblib")


def build_ml_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Engineers multi-indicator technical features from raw OHLCV DataFrame.
    """
    out = df.copy()
    if len(out) < 30:
        return pd.DataFrame()

    c = out["Close"].astype(float)
    h = out["High"].astype(float) if "High" in out.columns else c
    l = out["Low"].astype(float) if "Low" in out.columns else c
    v = out["Volume"].astype(float) if "Volume" in out.columns else pd.Series(1.0, index=out.index)

    # 1. RSI (14) & RSI Divergence (5-day diff)
    delta = c.diff()
    gain = delta.clip(lower=0).rolling(14).mean()
    loss = (-delta.clip(upper=0)).rolling(14).mean()
    out["RSI_14"] = 100 - (100 / (1 + gain / (loss + 1e-9)))
    out["RSI_Diff_5"] = out["RSI_14"].diff(5)

    # 2. MACD Momentum
    out["EMA_12"] = c.ewm(span=12, adjust=False).mean()
    out["EMA_26"] = c.ewm(span=26, adjust=False).mean()
    out["MACD"] = out["EMA_12"] - out["EMA_26"]
    out["MACD_Signal"] = out["MACD"].ewm(span=9, adjust=False).mean()
    out["MACD_Hist"] = out["MACD"] - out["MACD_Signal"]

    # 3. Bollinger Bands & Squeeze Metric
    out["BB_Mid"] = c.rolling(20).mean()
    out["BB_Std"] = c.rolling(20).std()
    out["BB_Upper"] = out["BB_Mid"] + 2 * out["BB_Std"]
    out["BB_Lower"] = out["BB_Mid"] - 2 * out["BB_Std"]
    out["BB_PctB"] = (c - out["BB_Lower"]) / (out["BB_Upper"] - out["BB_Lower"] + 1e-9)
    out["BB_Width"] = (out["BB_Upper"] - out["BB_Lower"]) / (out["BB_Mid"] + 1e-9)

    # 4. VWAP & Distance
    typical_price = (h + l + c) / 3.0
    out["VWAP"] = (typical_price * v).cumsum() / (v.cumsum() + 1e-9)
    out["VWAP_Dist"] = (c - out["VWAP"]) / (out["VWAP"] + 1e-9) * 100.0

    # 5. Volume Ratio vs 20-day SMA
    vol_sma20 = v.rolling(20).mean()
    out["Vol_Ratio"] = v / (vol_sma20 + 1e-9)

    # 6. ATR %
    hl = h - l
    hc = (h - c.shift()).abs()
    lc = (l - c.shift()).abs()
    atr = pd.concat([hl, hc, lc], axis=1).max(axis=1).rolling(14).mean()
    out["ATR_Pct"] = atr / (c + 1e-9) * 100.0

    # 7. SMA Distances
    out["SMA_20_Dist"] = (c - c.rolling(20).mean()) / (c.rolling(20).mean() + 1e-9) * 100.0
    out["SMA_50_Dist"] = (c - c.rolling(50).mean()) / (c.rolling(50).mean() + 1e-9) * 100.0
    out["SMA_200_Dist"] = (c - c.rolling(200).mean()) / (c.rolling(200).mean() + 1e-9) * 100.0

    # Return % features
    out["Return_1D"] = c.pct_change(1)
    out["Return_5D"] = c.pct_change(5)

    return out


class MLSignalClassifier:
    """
    Multi-Factor Machine Learning Signal Classifier with Model Persistence and AutoML.
    """

    FEATURE_COLS = [
        "RSI_14", "RSI_Diff_5", "MACD", "MACD_Signal", "MACD_Hist",
        "BB_PctB", "BB_Width", "VWAP_Dist", "Vol_Ratio", "ATR_Pct",
        "SMA_20_Dist", "SMA_50_Dist", "SMA_200_Dist", "Return_1D", "Return_5D"
    ]

    @classmethod
    def save_model(cls, model_payload: dict, file_path: str = DEFAULT_MODEL_PATH):
        """
        Saves trained model dictionary to disk using joblib.
        """
        try:
            joblib.dump(model_payload, file_path)
            return True
        except Exception:
            return False

    @classmethod
    def load_model(cls, file_path: str = DEFAULT_MODEL_PATH) -> dict:
        """
        Loads pre-trained model dictionary from disk.
        """
        if os.path.exists(file_path):
            try:
                return joblib.load(file_path)
            except Exception:
                return None
        return None

    @classmethod
    def train_and_predict(
        cls,
        df: pd.DataFrame,
        model_type: str = "Ensemble",
        use_automl: bool = False,
        use_disk_cache: bool = True
    ) -> dict:
        """
        Trains ML classifier or loads persisted model weights to output signal probabilities.
        """
        feat_df = build_ml_features(df)
        if feat_df.empty or len(feat_df) < 60:
            return {
                "signal": "HOLD", "confidence": 50.0, "buy_prob": 33.3, "sell_prob": 33.3, "hold_prob": 33.4,
                "model_used": model_type, "accuracy": 50.0, "feature_importances": pd.DataFrame(),
                "squeeze_active": False, "divergence_active": False,
                "error": "Insufficient historical data for ML training."
            }

        # Check for persisted model weights on disk
        persisted_payload = cls.load_model() if use_disk_cache else None

        # Create target label: 5-day forward return
        fwd_return = feat_df["Close"].pct_change(5).shift(-5)
        conditions = [fwd_return > 0.015, fwd_return < -0.015]
        feat_df["Target"] = np.select(conditions, [1, -1], default=0)

        train_data = feat_df.dropna(subset=cls.FEATURE_COLS + ["Target"])
        if len(train_data) < 40:
            return {
                "signal": "HOLD", "confidence": 50.0, "buy_prob": 33.3, "sell_prob": 33.3, "hold_prob": 33.4,
                "model_used": model_type, "accuracy": 50.0, "feature_importances": pd.DataFrame(),
                "squeeze_active": False, "divergence_active": False,
                "error": "Insufficient valid feature samples."
            }

        X = train_data[cls.FEATURE_COLS]
        y = train_data["Target"].astype(int)

        rf_model = None
        xgb_model = None
        test_acc = 50.0

        if persisted_payload and not use_automl:
            rf_model = persisted_payload.get("rf_model")
            xgb_model = persisted_payload.get("xgb_model")
            test_acc = persisted_payload.get("accuracy", 65.0)

        if rf_model is None:
            if use_automl:
                tuner_res = AutoMLTuner.tune_models(X, y)
                if not tuner_res.get("error"):
                    rf_model = tuner_res["best_rf"]
                    xgb_model = tuner_res["best_xgb"]
                    test_acc = max(tuner_res["rf_cv_accuracy"], tuner_res["xgb_cv_accuracy"])
            
            if rf_model is None:
                split_idx = int(len(X) * 0.8)
                X_train, X_test = X.iloc[:split_idx], X.iloc[split_idx:]
                y_train, y_test = y.iloc[:split_idx], y.iloc[split_idx:]

                rf_model = RandomForestClassifier(n_estimators=120, max_depth=6, random_state=42)
                rf_model.fit(X_train, y_train)
                rf_acc = rf_model.score(X_test, y_test) * 100.0

                if HAS_XGB and model_type in ["XGBoost", "Ensemble"]:
                    try:
                        xgb_model = XGBClassifier(
                            n_estimators=100, max_depth=4, learning_rate=0.05,
                            eval_metric="mlogloss", random_state=42
                        )
                        xgb_model.fit(X_train, y_train + 1)
                        xgb_acc = xgb_model.score(X_test, y_test + 1) * 100.0
                        test_acc = (rf_acc + xgb_acc) / 2.0
                    except Exception:
                        xgb_model = None
                        test_acc = rf_acc
                else:
                    test_acc = rf_acc

            # Save newly trained model to disk
            cls.save_model({
                "rf_model": rf_model,
                "xgb_model": xgb_model,
                "accuracy": round(float(test_acc), 1),
                "feature_cols": cls.FEATURE_COLS
            })

        # Latest feature vector (most recent bar)
        latest_x = feat_df[cls.FEATURE_COLS].iloc[[-1]].fillna(0)

        # Predict probabilities
        rf_probs = rf_model.predict_proba(latest_x)[0]
        prob_dict = {-1: 0.0, 0: 0.0, 1: 0.0}
        for cls_lbl, prob in zip(rf_model.classes_, rf_probs):
            prob_dict[cls_lbl] = prob

        if xgb_model is not None:
            xgb_probs = xgb_model.predict_proba(latest_x)[0]
            xgb_classes = [c - 1 for c in xgb_model.classes_]
            for cls_lbl, prob in zip(xgb_classes, xgb_probs):
                prob_dict[cls_lbl] = (prob_dict[cls_lbl] + prob) / 2.0

        sell_p = prob_dict[-1] * 100.0
        hold_p = prob_dict[0] * 100.0
        buy_p = prob_dict[1] * 100.0

        if buy_p >= max(sell_p, hold_p):
            pred_signal = "BUY"
            confidence = buy_p
        elif sell_p >= max(buy_p, hold_p):
            pred_signal = "SELL"
            confidence = sell_p
        else:
            pred_signal = "HOLD"
            confidence = hold_p

        # Feature importances
        importances = rf_model.feature_importances_
        fi_df = pd.DataFrame({
            "Feature": cls.FEATURE_COLS,
            "Importance": importances
        }).sort_values("Importance", ascending=False)

        # Check Bollinger Band Squeeze & RSI Divergence
        last_row = feat_df.iloc[-1]
        bb_w = float(last_row.get("BB_Width", 0))
        bb_w_min = float(feat_df["BB_Width"].tail(100).min()) if "BB_Width" in feat_df else 0
        squeeze_active = bb_w <= (bb_w_min * 1.15) if bb_w > 0 else False

        rsi_diff = float(last_row.get("RSI_Diff_5", 0))
        divergence_active = abs(rsi_diff) >= 8.0

        return {
            "signal": pred_signal,
            "confidence": round(float(confidence), 1),
            "buy_prob": round(float(buy_p), 1),
            "sell_prob": round(float(sell_p), 1),
            "hold_prob": round(float(hold_p), 1),
            "model_used": "XGBoost + Random Forest (AutoML Persisted)" if xgb_model is not None else "Random Forest (AutoML Persisted)",
            "accuracy": round(float(test_acc), 1),
            "feature_importances": fi_df,
            "squeeze_active": squeeze_active,
            "divergence_active": divergence_active,
            "error": None
        }
