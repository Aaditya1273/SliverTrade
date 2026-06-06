"""
SilverTrade AI — LSTM Signal Model
====================================
Sequence-to-label classifier using PyTorch LSTM.
Takes the last N candles as a sequence and predicts
STRONG_BUY / BUY / HOLD / SELL / STRONG_SELL.

Because PyTorch is a heavy dependency, the model is lazy-loaded
and gracefully degrades when PyTorch is unavailable.
"""

import json
import logging
import math
import os
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
    signal classes: STRONG_SELL, SELL, HOLD, BUY, STRONG_BUY.

    If PyTorch is not installed or no checkpoint exists, operates in
    untrained mode (returns HOLD with 0 confidence).
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
        """Check for PyTorch and try to load model checkpoint."""
        try:
            import torch
            self._torch_available = True

            if not os.path.exists(self.model_path):
                logger.info("LSTM checkpoint not found at %s — running in untrained mode", self.model_path)
                return

            if os.path.exists(DEFAULT_CONFIG_PATH):
                with open(DEFAULT_CONFIG_PATH) as f:
                    self.config = json.load(f)

            import joblib
            scaler_path = DEFAULT_SCALER_PATH
            if os.path.exists(scaler_path):
                self.scaler = joblib.load(scaler_path)

            model = _create_lstm_model(
                input_size=self.config.get("input_size", 10),
                hidden_size=self.config.get("hidden_size", 64),
                num_layers=self.config.get("num_layers", 2),
                num_classes=5,
            )
            self.model = model
            self.model.load_state_dict(torch.load(self.model_path, map_location="cpu"))
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

    @property
    def is_trained(self) -> bool:
        return self._trained and self.model is not None

    def _build_sequence(self, ohlcv: List[Dict[str, Any]]) -> Optional[Any]:
        """Build a normalised feature sequence from OHLCV data.

        Returns None if insufficient data or PyTorch unavailable.
        """
        if not self._torch_available or len(ohlcv) < SEQUENCE_LENGTH:
            return None

        import torch

        sequence = ohlcv[-SEQUENCE_LENGTH:]
        features = []
        for candle in sequence:
            features.append([
                float(candle.get("open", 0)),
                float(candle.get("high", 0)),
                float(candle.get("low", 0)),
                float(candle.get("close", 0)),
                float(candle.get("volume", 0)),
                float(candle.get("rsi", 0)),
                float(candle.get("ema_9", 0)),
                float(candle.get("ema_21", 0)),
                float(candle.get("macd", 0)),
                float(candle.get("atr", 0)),
            ])

        n_features = len(features[0]) if features else 1
        arr = torch.tensor(features, dtype=torch.float32).unsqueeze(0)

        if self.scaler:
            flat = arr.view(-1, n_features).numpy()
            scaled = self.scaler.transform(flat)
            arr = torch.tensor(scaled, dtype=torch.float32).view(1, SEQUENCE_LENGTH, n_features)

        return arr

    def predict(self, ohlcv: List[Dict[str, Any]]) -> Tuple[Optional[str], float]:
        """Predict trading signal from a sequence of OHLCV candles.

        Args:
            ohlcv: List of OHLCV dicts (oldest → newest, at least 60 candles)

        Returns:
            Tuple of (signal, confidence):
              signal: 'STRONG_BUY' | 'BUY' | 'HOLD' | 'SELL' | 'STRONG_SELL' | None
              confidence: 0.0–1.0 softmax probability of the predicted class
        """
        if not self.is_trained or not self._torch_available:
            return None, 0.0

        try:
            import torch
            sequence = self._build_sequence(ohlcv)
            if sequence is None:
                return None, 0.0

            with torch.no_grad():
                output = self.model(sequence)
                probabilities = torch.softmax(output, dim=1)
                confidence, predicted = torch.max(probabilities, dim=1)
                signal = SIGNAL_MAP.get(predicted.item(), "HOLD")
                return signal, float(confidence.item())

        except Exception as e:
            logger.warning("LSTM prediction failed: %s", e)
            return None, 0.0


def _create_lstm_model(input_size: int, hidden_size: int, num_layers: int, num_classes: int):
    """Create an LSTM PyTorch module. Only importable when torch is available."""
    import torch
    from torch import nn

    class _LSTMModel(nn.Module):
        """Internal PyTorch LSTM module."""

        def __init__(self, input_size: int, hidden_size: int, num_layers: int, num_classes: int):
            super().__init__()
            self.lstm = nn.LSTM(
                input_size=input_size,
                hidden_size=hidden_size,
                num_layers=num_layers,
                batch_first=True,
                dropout=0.2 if num_layers > 1 else 0,
            )
            self.fc = nn.Linear(hidden_size, num_classes)
            self.dropout = nn.Dropout(0.3)

        def forward(self, x):
            out, _ = self.lstm(x)
            out = self.dropout(out[:, -1, :])
            return self.fc(out)

    return _LSTMModel(input_size, hidden_size, num_layers, num_classes)
