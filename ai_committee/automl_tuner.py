"""
XERCES AutoML & Hyperparameter Tuning Module
Uses RandomizedSearchCV for hyperparameter optimization across Random Forest and XGBoost architectures.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import RandomizedSearchCV

try:
    from xgboost import XGBClassifier
    HAS_XGB = True
except ImportError:
    HAS_XGB = False


class AutoMLTuner:
    """
    Automated Machine Learning (AutoML) Hyperparameter Optimization Engine.
    """

    @classmethod
    def tune_models(cls, X: pd.DataFrame, y: pd.Series, cv: int = 3, n_iter: int = 8) -> dict:
        """
        Executes cross-validation randomized grid search to find optimal hyperparameters.
        """
        if len(X) < 50:
            return {"error": "Insufficient sample size for hyperparameter tuning (minimum 50 bars required)."}

        # 1. Random Forest Hyperparameter Grid
        rf_param_grid = {
            "n_estimators": [60, 100, 150, 200],
            "max_depth": [4, 6, 8, 10, None],
            "min_samples_split": [2, 5, 10],
            "criterion": ["gini", "entropy"]
        }

        rf_base = RandomForestClassifier(random_state=42)
        rf_search = RandomizedSearchCV(
            estimator=rf_base,
            param_distributions=rf_param_grid,
            n_iter=n_iter,
            cv=cv,
            scoring="accuracy",
            random_state=42,
            n_jobs=-1
        )
        rf_search.fit(X, y)

        best_rf = rf_search.best_estimator_
        best_rf_params = rf_search.best_params_
        best_rf_score = rf_search.best_score_ * 100.0

        # 2. XGBoost Hyperparameter Grid (if available)
        best_xgb = None
        best_xgb_params = {}
        best_xgb_score = 0.0

        if HAS_XGB:
            try:
                y_mapped = y + 1  # Map {-1, 0, 1} to {0, 1, 2}
                xgb_param_grid = {
                    "n_estimators": [50, 100, 150],
                    "max_depth": [3, 4, 6, 8],
                    "learning_rate": [0.01, 0.03, 0.05, 0.1],
                    "subsample": [0.7, 0.85, 1.0],
                    "colsample_bytree": [0.7, 0.85, 1.0]
                }
                xgb_base = XGBClassifier(eval_metric="mlogloss", random_state=42)
                xgb_search = RandomizedSearchCV(
                    estimator=xgb_base,
                    param_distributions=xgb_param_grid,
                    n_iter=n_iter,
                    cv=cv,
                    scoring="accuracy",
                    random_state=42,
                    n_jobs=-1
                )
                xgb_search.fit(X, y_mapped)

                best_xgb = xgb_search.best_estimator_
                best_xgb_params = xgb_search.best_params_
                best_xgb_score = xgb_search.best_score_ * 100.0
            except Exception:
                best_xgb = None

        return {
            "best_rf": best_rf,
            "best_rf_params": best_rf_params,
            "rf_cv_accuracy": round(float(best_rf_score), 2),
            "best_xgb": best_xgb,
            "best_xgb_params": best_xgb_params,
            "xgb_cv_accuracy": round(float(best_xgb_score), 2) if best_xgb else 0.0,
            "error": None
        }
