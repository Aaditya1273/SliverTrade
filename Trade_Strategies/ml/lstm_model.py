"""
SilverTrade AI — LSTM Signal Model
====================================
Sequence-to-label classifier using PyTorch LSTM.
Takes the last N candles as a sequence and predicts
STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL.

Auto-trains on realistic synthetic data if no checkpoint exists.
Gracefully degrades when PyTorch is unavailable.
"""

import json
import logging
import math
import os
import random
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
DEFAULT_MODEL_PATH = os.path.join(MODEL_DIR, "lstm.pt")
DEFAULT_SCALER_PATH = os.path.join(MODEL_DIR, "lstm_scaler.pkl")
DEFAULT_CONFIG_PATH = os.path.join(MODEL_DIR, "lstm_config.json")

SEQUENCE_LENGTH = 60
SIGNAL_MAP = {0: "STRONG_SELL", 1: "SELL", 2: "HOLD", 3: "BUY", 4: "STRONG_BUY"}


class LSTMSignalModel:
    """LSTM-based sequence classifier for trading signals.

    Takes a sequence of the last N OHLCV candles and predicts one of 5
    signal classes. Auto-trains on realistic synthetic data when no
    checkpoint exists. Uses sklearn LabelEncoder for normalization
    when PyTorch scaler is unavailable.
    """

    def __init__(self, model_path: str = DEFAULT_MODEL_PATH):
        self.model_path = model_path
        self.model = None
        self.scaler = None
        self.config: Dict[str, Any] = {}
        self._trained = False
        self._torch_available = False
        self._load_dependencies()

    def _load_dependencies(self) -> None:
        try:
            import torch
            self._torch_available = True

            if not os.path.exists(self.model_path):
                logger.info("LSTM checkpoint not found — attempting auto-train")
                self._auto_train()
                if not os.path.exists(self.model_path):
                    logger.info("LSTM auto-train failed or PyTorch unavailable — running untrained")
                    return

            if os.path.exists(DEFAULT_CONFIG_PATH):
                with open(DEFAULT_CONFIG_PATH) as f:
                    self.config = json.load(f)

            import joblib
            if os.path.exists(DEFAULT_SCALER_PATH):
                self.scaler = joblib.load(DEFAULT_SCALER_PATH)

            model = _create_lstm_model(
                input_size=self.config.get("input_size", 10),
                hidden_size=self.config.get("hidden_size", 64),
                num_layers=self.config.get("num_layers", 2),
                num_classes=5,
            )
            self.model = model
            import torch
            self.model.load_state_dict(
                torch.load(self.model_path, map_location="cpu", weights_only=True)
            )
            self.model.eval()
            self._trained = True
            logger.info("LSTM model loaded from %s", self.model_path)

        except ImportError:
            logger.info("PyTorch not installed — LSTM model unavailable")
            self._torch_available = False
        except Exception as e:
            logger.error("Failed to load LSTM model: %s", e)
            self.model = None
            self._trained = False

    def _auto_train(self) -> None:
        """Auto-train LSTM on realistic synthetic data when no checkpoint exists."""
        try:
            from ml.lstm_train import train_lstm
            logger.info("Auto-training LSTM on synthetic data...")
            ohlcv = self._generate_training_data()
            if len(ohlcv) >= 500:
                result = train_lstm(ohlcv)
                if "error" not in result:
                    logger.info("LSTM auto-training complete")
                else:
                    logger.warning("LSTM auto-train failed: %s", result["error"])
        except ImportError:
            logger.info("LSTM train module not available")
        except Exception as e:
            logger.warning("LSTM auto-train error: %s", e)

    def _generate_training_data(self, candles: int = 3000) -> List[Dict[str, Any]]:
        """Generate realistic synthetic OHLCV data with regime changes."""
        data = []
        price = 50000.0
        ts = int(datetime.now(timezone.utc).timestamp()) - candles * 900
        vol = 0.015
        trend = 0.0001
        regime_len = 0

        for i in range(candles):
            if regime_len <= 0:
                regime = random.choices(
                    ["bull", "bear", "side", "highvol"],
                    weights=[0.3, 0.25, 0.3, 0.15],
                )[0]
                regime_len = random.randint(50, 300)
                if regime == "bull":
                    trend, vol = random.gauss(0.0003, 0.0002), random.gauss(0.012, 0.003)
                elif regime == "bear":
                    trend, vol = random.gauss(-0.0003, 0.0002), random.gauss(0.015, 0.004)
                elif regime == "side":
                    trend, vol = random.gauss(0, 0.00005), random.gauss(0.008, 0.002)
                else:
                    trend, vol = random.gauss(0, 0.0004), random.gauss(0.03, 0.008)
            regime_len -= 1

            ret = trend + random.gauss(0, vol)
            if random.random() < 0.02:
                ret *= 3
            price *= math.exp(ret)
            price = max(price, 1.0)

            data.append({
                "time": ts + i * 900,
                "open": round(price * (1 + random.gauss(0, vol * 0.3)), 2),
                "high": round(price * (1 + abs(random.gauss(0, vol * 0.4))), 2),
                "low": round(price * (1 - abs(random.gauss(0, vol * 0.4))), 2),
                "close": round(price, 2),
                "volume": round(random.lognormvariate(math.log(1000), 0.5) * (1 + abs(ret) * 10), 2),
            })

        return data

    @property
    def is_trained(self) -> bool:
        return self._trained and self.model is not None

    def _build_sequence(self, ohlcv: List[Dict[str, Any]]) -> Optional[Any]:
        if not self._torch_available or len(ohlcv) < SEQUENCE_LENGTH:
            return None

        try:
            import numpy as np
            recent = ohlcv[-SEQUENCE_LENGTH:]
            features = []
            for c in recent:
                features.append([
                    c.get("open", 0), c.get("high", 0), c.get("low", 0),
                    c.get("close", 0), c.get("volume", 0),
                ])
            arr = np.array(features, dtype=np.float32)

            if self.scaler is not None:
                flat = arr.reshape(-1, 5)
                scaled = self.scaler.transform(flat)
                arr = scaled.reshape(SEQUENCE_LENGTH, 5)
            else:
                for i in range(5):
                    col = arr[:, i]
                    mn, mx = col.min(), col.max()
                    if mx > mn:
                        arr[:, i] = (col - mn) / (mx - mn)
                    else:
                        arr[:, i] = 0

            import torch
            return torch.FloatTensor(arr).unsqueeze(0)

        except Exception as e:
            logger.debug("Failed to build LSTM sequence: %s", e)
            return None

    def predict(self, ohlcv: List[Dict[str, Any]]) -> Tuple[Optional[str], float]:
        if not self.is_trained:
            return None, 0.0

        try:
            import torch
            sequence = self._build_sequence(ohlcv)
            if sequence is None:
                return None, 0.0

            with torch.no_grad():
                output = self.model(sequence)
                probs = torch.softmax(output, dim=1)[0]
                confidence, predicted = torch.max(probs, 0)
                signal = SIGNAL_MAP.get(predicted.item(), "HOLD")

            return signal, round(confidence.item(), 4)

        except Exception as e:
            logger.warning("LSTM prediction failed: %s", e)
            return None, 0.0


def _create_lstm_model(input_size: int, hidden_size: int, num_layers: int, num_classes: int) -> Any:
    """Create a PyTorch LSTM model for signal classification."""
    import torch
    import torch.nn as nn

    class LSTMClassifier(nn.Module):
        def __init__(self):
            super().__init__()
            self.lstm = nn.LSTM(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                batch_first=True,
                dropout=0.3 if num_layers > 1 else 0,
            )
            self.dropout = nn.Dropout(0.3)
            self.fc = nn.Linear(hidden_size, num_classes)

        def forward(self, x):
            out, _ = self.lstm(x)
            out = self.dropout(out[:, -1, :])
            out = self.fc(out)
            return out

    return LSTMClassifier()
