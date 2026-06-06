"""
SilverTrade AI — Random Forest Signal Model
=============================================
Trained on technical indicator features to predict directional price movement.
Produces calibrated probability scores that feed into the ensemble decision.

SAFETY: All prediction methods return (None, 0.0) on any error so the
calling ensemble never receives invalid data.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
DEFAULT_MODEL_PATH = os.path.join(MODEL_DIR, "random_forest.pkl")
DEFAULT_FEATURES_PATH = os.path.join(MODEL_DIR, "rf_features.json")


class RandomForestSignalModel:
    """Random Forest classifier for directional price prediction.

    Uses technical indicator values as features to predict whether price
    will be higher 4 candles from now (binary classification).

    The model is loaded from a joblib checkpoint on init. If the checkpoint
    does not exist, the model operates in "untrained" mode — all predictions
    return (None, 0.0) and the ensemble falls back to rule-based scoring.
    """

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH, features_path: str = DEFAULT_FEATURES_PATH):
        self.model_path = model_path
        self.features_path = features_path
        self.model = None
        self.feature_names: List[str] = []
        self._trained = False
        self._load_model()

    def _load_model(self) -> None:
        """Load a trained model checkpoint from disk. No-op if file missing."""
        if not os.path.exists(self.model_path):
            logger.info("Random Forest checkpoint not found at %s — running in untrained mode", self.model_path)
            return
        try:
            import joblib
            self.model = joblib.load(self.model_path)
            if os.path.exists(self.features_path):
                with open(self.features_path) as f:
                    self.feature_names = json.load(f)
            self._trained = True
            logger.info("Random Forest model loaded from %s (%d features)", self.model_path, len(self.feature_names))
        except Exception as e:
            logger.error("Failed to load Random Forest model: %s", e)
            self.model = None
            self._trained = False

    @property
    def is_trained(self) -> bool:
        """Whether a trained model checkpoint is loaded."""
        return self._trained and self.model is not None

    def _build_feature_vector(self, indicators: Dict[str, Any]) -> np.ndarray:
        """Build a flat feature vector from indicator values.

        Falls back to 0 for any missing indicator so partial data does
        not crash prediction.
        """
        if not self.feature_names:
            return np.zeros((1, 1))
        values = []
        for name in self.feature_names:
            values.append(float(indicators.get(name, 0.0)))
        return np.array([values])

    def predict(self, indicators: Dict[str, Any]) -> Tuple[Optional[str], float]:
        """Predict directional price movement.

        Args:
            indicators: Dict of indicator values (rsi, ema_9, ema_21, macd, etc.)

        Returns:
            Tuple of (direction, confidence):
              direction: 'UP' | 'DOWN' | None (None if model not trained)
              confidence: 0.0–1.0 calibrated probability
        """
        if not self.is_trained:
            return None, 0.0

        try:
            X = self._build_feature_vector(indicators)
            proba = self.model.predict_proba(X)[0]
            # proba[0] = probability of DOWN, proba[1] = probability of UP
            idx_up = 1 if len(proba) > 1 else 0
            idx_down = 0 if len(proba) > 1 else 0
            if proba[idx_up] >= proba[idx_down]:
                return "UP", float(proba[idx_up])
            else:
                return "DOWN", float(proba[idx_down])
        except Exception as e:
            logger.warning("Random Forest prediction failed: %s", e)
            return None, 0.0


def train_random_forest(
    ohlcv_list: List[Dict[str, Any]],
    lookahead: int = 4,
    save_path: str = DEFAULT_MODEL_PATH,
    features_path: str = DEFAULT_FEATURES_PATH,
) -> Dict[str, Any]:
    """Train a Random Forest model on historical OHLCV data.

    Each row: indicator values at candle N → target = 1 if close[N+lookahead] > close[N].

    Args:
        ohlcv_list: List of OHLCV candles (sorted oldest → newest)
        lookahead: Number of candles ahead to predict
        save_path: Where to save the trained model
        features_path: Where to save the feature names list

    Returns:
        Training metrics dict, or error dict on failure
    """
    try:
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.model_selection import train_test_split
        from sklearn.metrics import accuracy_score, precision_score, recall_score
        import joblib

        from strategy_engine import StrategyEngine
        engine = StrategyEngine()

        if len(ohlcv_list) < 100:
            return {"error": f"Insufficient data: {len(ohlcv_list)} candles (need 100+)"}

        features_list = []
        targets = []

        # Feature columns we extract
        feature_cols = [
            "rsi", "ema_9", "ema_21", "ema_50",
            "macd", "signal",
            "bb_upper", "bb_lower", "atr",
        ]

        for i in range(50, len(ohlcv_list) - lookahead):
            window = ohlcv_list[: i + 1]
            result = engine.analyze("TRAINING", window, "TRAINING")
            if not result or not result.get("indicators"):
                continue

            ind = result["indicators"]
            feature_vector = [ind.get(col, 0.0) for col in feature_cols]
            features_list.append(feature_vector)

            future_close = ohlcv_list[i + lookahead].get("close", 0)
            current_close = ohlcv_list[i].get("close", 0)
            target = 1 if future_close > current_close else 0
            targets.append(target)

        if len(features_list) < 50:
            return {"error": f"Only {len(features_list)} training samples (need 50+)"}

        X = np.array(features_list)
        y = np.array(targets)

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.2, random_state=42, shuffle=False
        )

        model = RandomForestClassifier(
            n_estimators=200,
            max_depth=10,
            min_samples_leaf=5,
            random_state=42,
            class_weight="balanced",
            n_jobs=-1,
        )
        model.fit(X_train, y_train)

        y_pred = model.predict(X_test)
        accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)

        os.makedirs(os.path.dirname(save_path), exist_ok=True)
        joblib.dump(model, save_path)
        with open(features_path, "w") as f:
            json.dump(feature_cols, f)

        logger.info("Random Forest trained: accuracy=%.3f, precision=%.3f, recall=%.3f", accuracy, precision, recall)

        return {
            "status": "success",
            "accuracy": round(accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "samples": len(features_list),
            "test_samples": len(y_test),
            "features": feature_cols,
            "saved_to": save_path,
        }

    except ImportError as e:
        return {"error": f"Missing dependency: {e}. Install scikit-learn."}
    except Exception as e:
        logger.exception("Random Forest training failed")
        return {"error": str(e)}
