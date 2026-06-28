"""
SilverTrade AI — Random Forest Signal Model
=============================================
Trained on technical indicator features to predict directional price movement.
Produces calibrated probability scores that feed into the ensemble decision.

FIXES:
  1. Realistic synthetic data (geometric Brownian motion + regimes)
  2. Out-of-sample validation (70/30 train/test split)
  3. Confidence calibration (Platt scaling + bucket calibration)
  4. Regime-aware feature engineering
"""

import json
import logging
import math
import os
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

import numpy as np

from indicators import adx, atr, bollinger_bands, ema, macd, rsi, sma

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
DEFAULT_MODEL_PATH = os.path.join(MODEL_DIR, "random_forest.pkl")
DEFAULT_FEATURES_PATH = os.path.join(MODEL_DIR, "rf_features.json")
DEFAULT_METRICS_PATH = os.path.join(MODEL_DIR, "rf_metrics.json")


class RandomForestSignalModel:
    """Random Forest classifier for directional price prediction.

    Uses technical indicator values as features to predict whether price
    will be higher 4 candles from now (binary classification).

    Training uses realistic synthetic data when real data is unavailable,
    with proper train/test split and Platt-calibrated probabilities.
    """

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH, features_path: str = DEFAULT_FEATURES_PATH):
        self.model_path = model_path
        self.features_path = features_path
        self.metrics_path = DEFAULT_METRICS_PATH
        self.model = None
        self.feature_names: List[str] = []
        self._trained = False
        self._calibration_buckets: Dict[str, float] = {}
        self._out_of_sample_score: float = 0.0
        self._validation_metrics: Dict[str, Any] = {}
        self._load_model()

    def _load_model(self) -> None:
        """Load a trained model checkpoint from disk. No-op if file missing."""
        if not os.path.exists(self.model_path):
            logger.info("Random Forest checkpoint not found — running in untrained mode")
            return
        try:
            import joblib
            self.model = joblib.load(self.model_path)
            if os.path.exists(self.features_path):
                with open(self.features_path) as f:
                    self.feature_names = json.load(f)
            if os.path.exists(self.metrics_path):
                with open(self.metrics_path) as f:
                    metrics = json.load(f)
                    self._out_of_sample_score = metrics.get("out_of_sample_accuracy", 0)
                    self._calibration_buckets = metrics.get("calibration_buckets", {})
                    self._validation_metrics = metrics.get("validation_metrics", {})
            self._trained = True
            logger.info("RF model loaded (%d features, OOS accuracy: %.1f%%)",
                        len(self.feature_names), self._out_of_sample_score * 100)
        except Exception as e:
            logger.error("Failed to load Random Forest model: %s", e)
            self.model = None
            self._trained = False

    @property
    def is_trained(self) -> bool:
        return self._trained and self.model is not None

    def train(self, force_retrain: bool = False) -> Dict[str, Any]:
        """Train the model on realistic synthetic data.

        Generates market-like price data with different regimes,
        computes indicators, and trains with 70/30 train/test split.
        Calibrates confidence scores against out-of-sample performance.
        """
        from sklearn.ensemble import RandomForestClassifier
        from sklearn.calibration import CalibratedClassifierCV
        from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score, confusion_matrix
        from sklearn.model_selection import train_test_split

        if self._trained and not force_retrain:
            return {"status": "skipped", "message": "Model already trained"}

        logger.info("Generating realistic synthetic market data for training...")
        ohlcv = self._generate_realistic_data(candles=5000)

        logger.info("Computing features across %d candles...", len(ohlcv))
        X, y = self._prepare_training_data(ohlcv)

        if len(X) < 200:
            return {"status": "error", "message": f"Only {len(X)} samples — need at least 200"}

        X_train, X_test, y_train, y_test = train_test_split(
            X, y, test_size=0.3, shuffle=False, random_state=42
        )

        n_estimators = min(300, max(50, len(X_train) // 10))
        rf = RandomForestClassifier(
            n_estimators=n_estimators,
            max_depth=min(15, max(5, len(self.feature_names) * 2)),
            min_samples_leaf=5,
            min_samples_split=10,
            class_weight="balanced",
            random_state=42,
            n_jobs=-1,
        )
        rf.fit(X_train, y_train)

        calibrated = CalibratedClassifierCV(rf, method="sigmoid", cv=5)
        calibrated.fit(X_train, y_train)

        y_pred = calibrated.predict(X_test)
        y_proba = calibrated.predict_proba(X_test)

        oos_accuracy = accuracy_score(y_test, y_pred)
        precision = precision_score(y_test, y_pred, zero_division=0)
        recall = recall_score(y_test, y_pred, zero_division=0)
        f1 = f1_score(y_test, y_pred, zero_division=0)
        cm = confusion_matrix(y_test, y_pred).tolist()

        self._compute_calibration_buckets(y_test, y_proba)

        os.makedirs(MODEL_DIR, exist_ok=True)
        import joblib
        joblib.dump(calibrated, self.model_path)

        self.feature_names = list(range(X.shape[1]))
        with open(self.features_path, "w") as f:
            json.dump(self.feature_names, f)

        self._out_of_sample_score = oos_accuracy
        self._validation_metrics = {
            "out_of_sample_accuracy": round(oos_accuracy, 4),
            "precision": round(precision, 4),
            "recall": round(recall, 4),
            "f1_score": round(f1, 4),
            "confusion_matrix": cm,
            "train_samples": len(X_train),
            "test_samples": len(X_test),
            "n_estimators": n_estimators,
            "feature_count": X.shape[1],
        }
        metrics = {
            "out_of_sample_accuracy": oos_accuracy,
            "calibration_buckets": self._calibration_buckets,
            "validation_metrics": self._validation_metrics,
        }
        with open(self.metrics_path, "w") as f:
            json.dump(metrics, f, indent=2)

        self.model = calibrated
        self._trained = True

        logger.info("RF training complete — OOS accuracy: %.1f%%, precision: %.1f%%, recall: %.1f%%",
                    oos_accuracy * 100, precision * 100, recall * 100)
        return {"status": "success", "metrics": self._validation_metrics}

    def _generate_realistic_data(self, candles: int = 5000) -> List[Dict[str, Any]]:
        """Generate realistic OHLCV data using geometric Brownian motion with regime changes."""
        data: List[Dict[str, Any]] = []
        price = 50000.0
        timestamp = int(datetime.now(timezone.utc).timestamp()) - candles * 900

        volatility = 0.015
        trend = 0.0001
        regime_length = 0

        for i in range(candles):
            if regime_length <= 0:
                regime = random.choices(
                    ["bull", "bear", "sideways", "high_vol"],
                    weights=[0.3, 0.25, 0.3, 0.15],
                )[0]
                regime_length = random.randint(50, 300)
                if regime == "bull":
                    trend = random.gauss(0.0003, 0.0002)
                    volatility = random.gauss(0.012, 0.003)
                elif regime == "bear":
                    trend = random.gauss(-0.0003, 0.0002)
                    volatility = random.gauss(0.015, 0.004)
                elif regime == "sideways":
                    trend = random.gauss(0, 0.00005)
                    volatility = random.gauss(0.008, 0.002)
                elif regime == "high_vol":
                    trend = random.gauss(0, 0.0004)
                    volatility = random.gauss(0.03, 0.008)
            regime_length -= 1

            drift = trend + random.gauss(0, volatility)
            shock = random.gauss(0, volatility * 0.5)
            if random.random() < 0.02:
                shock *= 3

            ret = drift + shock
            price *= math.exp(ret)
            price = max(price, 1.0)

            open_p = price * (1 + random.gauss(0, volatility * 0.3))
            high_p = max(open_p, price) * (1 + abs(random.gauss(0, volatility * 0.4)))
            low_p = min(open_p, price) * (1 - abs(random.gauss(0, volatility * 0.4)))
            close_p = price
            volume = random.lognormvariate(math.log(1000), 0.5) * (1 + abs(shock) * 10)

            data.append({
                "time": timestamp + i * 900,
                "open": round(open_p, 2),
                "high": round(max(high_p, open_p, close_p), 2),
                "low": round(min(low_p, open_p, close_p), 2),
                "close": round(close_p, 2),
                "volume": round(volume, 2),
            })

        return data

    def _prepare_training_data(self, ohlcv: List[Dict[str, Any]]) -> Tuple[np.ndarray, np.ndarray]:
        """Build feature matrix and labels from OHLCV data.

        Labels: 1 if price is higher 4 candles from now, 0 otherwise.
        """
        closes = [c["close"] for c in ohlcv]
        highs = [c["high"] for c in ohlcv]
        lows = [c["low"] for c in ohlcv]
        volumes = [c["volume"] for c in ohlcv]

        features = []
        labels = []
        lookahead = 4

        for i in range(60, len(ohlcv) - lookahead):
            c = closes[:i + 1]
            h = highs[:i + 1]
            l = lows[:i + 1]
            v = volumes[:i + 1]

            feat = self._compute_features(c, h, l, v)
            if feat is None:
                continue

            future_ret = (closes[i + lookahead] - closes[i]) / closes[i]
            label = 1 if future_ret > 0 else 0

            features.append(feat)
            labels.append(label)

        return np.array(features), np.array(labels)

    def _compute_features(self, closes, highs, lows, volumes) -> Optional[List[float]]:
        """Compute all technical indicators as a flat feature vector."""
        try:
            features = []

            rsi_vals = rsi(closes, 14)
            rsi_last = self._safe_last(rsi_vals) or 50
            features.extend([rsi_last / 100, (rsi_last - 50) / 50])

            ema9 = ema(closes, 9)
            ema21 = ema(closes, 21)
            ema50 = ema(closes, 50)
            e9 = self._safe_last(ema9) or 0
            e21 = self._safe_last(ema21) or 0
            e50 = self._safe_last(ema50) or 0
            features.extend([
                e9 / e21 if e21 else 1,
                e21 / e50 if e50 else 1,
                (e9 - e21) / (e21 or 1),
                (e21 - e50) / (e50 or 1),
            ])

            macd_line, signal_line, hist = macd(closes)
            ml = self._safe_last(macd_line) or 0
            sl = self._safe_last(signal_line) or 0
            hl = self._safe_last(hist) or 0
            features.extend([
                ml, sl, hl, ml - sl,
            ])

            bb_mid, bb_upper, bb_lower = bollinger_bands(closes)
            bm = self._safe_last(bb_mid) or 0
            bu = self._safe_last(bb_upper) or 0
            bl = self._safe_last(bb_lower) or 0
            last_c = closes[-1]
            bb_width = bu - bl
            features.extend([
                (last_c - bm) / (bb_width or 1),
                (last_c - bl) / (bb_width or 1) if bb_width else 0.5,
                (bu - bm) / (bm or 1),
            ])

            atr_vals = atr(highs, lows, closes)
            atr_last = self._safe_last(atr_vals) or 0
            avg_price = sum(closes[-20:]) / min(20, len(closes))
            features.append(atr_last / (avg_price or 1))

            adx_vals = adx(highs, lows, closes)
            adx_last = self._safe_last(adx_vals) or 0
            features.append(adx_last / 100)

            volume_ratio = 1.0
            if len(volumes) >= 20:
                avg_vol = sum(volumes[-20:]) / 20
                volume_ratio = volumes[-1] / avg_vol if avg_vol else 1
            features.append(min(volume_ratio, 5) / 5)

            returns = [(closes[i] - closes[i - 1]) / closes[i - 1]
                       for i in range(max(1, len(closes) - 20), len(closes))]
            if returns:
                features.append(sum(returns))
                features.append(np.std(returns) if len(returns) > 1 else 0)
            else:
                features.extend([0, 0])

            slope_5 = (closes[-1] - closes[-5]) / (closes[-5] or 1) if len(closes) >= 5 else 0
            slope_10 = (closes[-1] - closes[-10]) / (closes[-10] or 1) if len(closes) >= 10 else 0
            features.extend([slope_5, slope_10])

            return features

        except Exception:
            return None

    def _safe_last(self, values) -> Optional[float]:
        if not values:
            return None
        for v in reversed(values):
            if v is not None:
                return v
        return None

    def _compute_calibration_buckets(self, y_true: np.ndarray, y_proba: np.ndarray) -> None:
        """Compute calibration buckets: for each confidence range, what's the actual accuracy?"""
        if len(y_true) == 0:
            self._calibration_buckets = {
                "50_60": 0.55, "60_70": 0.65, "70_80": 0.75,
                "80_90": 0.85, "90_100": 0.90,
            }
            return

        buckets = [(0.5, 0.6), (0.6, 0.7), (0.7, 0.8), (0.8, 0.9), (0.9, 1.0)]
        bucket_labels = ["50_60", "60_70", "70_80", "80_90", "90_100"]

        for (lo, hi), label in zip(buckets, bucket_labels):
            mask = (y_proba[:, 1] >= lo) & (y_proba[:, 1] < hi)
            if mask.sum() > 0:
                actual_accuracy = y_true[mask].mean()
                self._calibration_buckets[label] = round(float(actual_accuracy), 4)
            else:
                self._calibration_buckets[label] = (lo + hi) / 2

    def _calibrate_confidence(self, raw_confidence: float) -> float:
        """Adjust raw model confidence using calibration bucketing.

        If the model says 85% confident but historically was only right
        70% of the time at that confidence, return 70% instead.
        """
        for lo, hi, label in [(0.5, 0.6, "50_60"), (0.6, 0.7, "60_70"),
                               (0.7, 0.8, "70_80"), (0.8, 0.9, "80_90"),
                               (0.9, 1.0, "90_100")]:
            if lo <= raw_confidence < hi:
                calibrated = self._calibration_buckets.get(label, raw_confidence)
                return min(calibrated, raw_confidence)
        return min(raw_confidence, 0.95)

    def predict(self, indicators: Dict[str, Any]) -> Tuple[Optional[str], float]:
        """Predict directional price movement with calibrated confidence.

        Returns:
            Tuple of (direction, confidence):
              direction: 'UP' | 'DOWN' | None
              confidence: 0.0–1.0 calibrated probability
        """
        if not self.is_trained:
            return None, 0.0

        try:
            X = self._build_feature_vector(indicators)
            proba = self.model.predict_proba(X)
            if proba is None or len(proba) == 0:
                return None, 0.0

            proba = proba[0]
            if proba is None or len(proba) < 2:
                return None, 0.0

            idx_up = 1
            idx_down = 0

            raw_confidence = float(max(proba[idx_up], proba[idx_down]))
            calibrated = self._calibrate_confidence(raw_confidence)

            if float(proba[idx_up]) >= float(proba[idx_down]):
                return "UP", round(calibrated, 4)
            else:
                return "DOWN", round(calibrated, 4)

        except Exception as e:
            logger.warning("RF prediction failed: %s", e)
            return None, 0.0

    def _build_feature_vector(self, indicators: Dict[str, Any]) -> np.ndarray:
        """Build feature vector from indicator values in the same order as training.

        Falls back to smart defaults for any missing indicator.
        """
        pass_through = [
            ("rsi_norm", indicators.get("rsi", 50) / 100),
            ("rsi_dev", (indicators.get("rsi", 50) - 50) / 50),
            ("ema_ratio_9_21", indicators.get("ema_fast", 0) / max(indicators.get("ema_slow", 1), 1)),
            ("ema_ratio_21_50", indicators.get("ema_slow", 0) / max(indicators.get("ema_50", 1), 1)),
            ("ema_diff_9_21", (indicators.get("ema_fast", 0) - indicators.get("ema_slow", 0)) / max(indicators.get("ema_slow", 1), 1)),
            ("ema_diff_21_50", (indicators.get("ema_slow", 0) - indicators.get("ema_50", 0)) / max(indicators.get("ema_50", 1), 1)),
            ("macd", indicators.get("macd", 0)),
            ("macd_signal", indicators.get("signal", 0)),
            ("macd_hist", indicators.get("macd", 0) - indicators.get("signal", 0)),
            ("macd_diff", (indicators.get("macd", 0) - indicators.get("signal", 0)) / max(abs(indicators.get("signal", 0)), 0.001)),
            ("bb_position", (indicators.get("price", 0) - indicators.get("bb_mid", 0)) / max(indicators.get("bb_upper", 0) - indicators.get("bb_lower", 0), 0.01)),
            ("bb_lower_dist", (indicators.get("price", 0) - indicators.get("bb_lower", 0)) / max(indicators.get("bb_upper", 0) - indicators.get("bb_lower", 0), 0.01)),
            ("bb_width", (indicators.get("bb_upper", 0) - indicators.get("bb_mid", 0)) / max(indicators.get("bb_mid", 0), 0.01)),
            ("atr_ratio", indicators.get("atr", 0) / max(indicators.get("price", 0), 1)),
            ("adx", indicators.get("adx", 0) / 100),
            ("volume_ratio", min(indicators.get("volume_ratio", 1), 5) / 5),
            ("price_return_20", indicators.get("return_20", 0)),
            ("volatility_20", indicators.get("volatility_20", 0)),
            ("slope_5", indicators.get("slope_5", 0)),
            ("slope_10", indicators.get("slope_10", 0)),
        ]

        values = [v for _, v in pass_through]
        return np.array([values])
