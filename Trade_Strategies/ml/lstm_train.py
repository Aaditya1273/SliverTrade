"""
SilverTrade AI — LSTM Training Pipeline
=========================================
Prepares sequences from OHLCV data, trains the LSTM model,
and saves the checkpoint + scaler to disk.

SAFETY: Gracefully returns an error dict if PyTorch is unavailable.
"""

import json
import logging
import os
from typing import Any, Dict, List, Optional

import numpy as np

logger = logging.getLogger(__name__)

MODEL_DIR = os.path.join(os.path.dirname(__file__), "models")
SEQUENCE_LENGTH = 60

SIGNAL_MAP = {"STRONG_SELL": 0, "SELL": 1, "HOLD": 2, "BUY": 3, "STRONG_BUY": 4}


def _is_torch_available() -> bool:
    try:
        import torch  # noqa: F401
        return True
    except ImportError:
        return False


def _prepare_sequences(ohlcv: List[Dict[str, Any]]) -> tuple:
    """Prepare training sequences and target labels from OHLCV data.

    Each sequence: last SEQUENCE_LENGTH candles normalised by feature.
    Target: signal class based on future price movement.

    Returns (X, y) numpy arrays or (None, None) on failure.
    """
    if len(ohlcv) < SEQUENCE_LENGTH + 10:
        return None, None

    def _future_signal(idx: int, lookahead: int = 4) -> int:
        """Label the signal at candle idx based on price lookahead candles ahead."""
        future_close = ohlcv[idx + lookahead].get("close", 0)
        current_close = ohlcv[idx].get("close", 0)
        if not current_close:
            return SIGNAL_MAP["HOLD"]

        pct_change = (future_close - current_close) / current_close * 100

        if pct_change > 2.0:
            return SIGNAL_MAP["STRONG_BUY"]
        elif pct_change > 0.5:
            return SIGNAL_MAP["BUY"]
        elif pct_change < -2.0:
            return SIGNAL_MAP["STRONG_SELL"]
        elif pct_change < -0.5:
            return SIGNAL_MAP["SELL"]
        else:
            return SIGNAL_MAP["HOLD"]

    sequences, targets = [], []
    for i in range(len(ohlcv) - SEQUENCE_LENGTH - 4):
        seq = ohlcv[i: i + SEQUENCE_LENGTH]
        features = []
        for candle in seq:
            features.append([
                float(candle.get("open", 0)),
                float(candle.get("high", 0)),
                float(candle.get("low", 0)),
                float(candle.get("close", 0)),
                float(candle.get("volume", 0)),
            ])
        sequences.append(features)
        targets.append(_future_signal(i + SEQUENCE_LENGTH - 1))

    if len(sequences) < 10:
        return None, None

    return np.array(sequences, dtype=np.float32), np.array(targets, dtype=np.int64)


def train_lstm(
    ohlcv: List[Dict[str, Any]],
    save_path: str = os.path.join(MODEL_DIR, "lstm.pt"),
    epochs: int = 50,
    batch_size: int = 32,
    learning_rate: float = 0.001,
) -> Dict[str, Any]:
    """Train the LSTM model on historical OHLCV data.

    Args:
        ohlcv: List of OHLCV candles (sorted oldest → newest)
        save_path: Where to save the trained model checkpoint
        epochs: Number of training epochs
        batch_size: Batch size for training
        learning_rate: Adam learning rate

    Returns:
        Metrics dict with accuracy and loss, or error dict on failure
    """
    if not _is_torch_available():
        return {"error": "PyTorch is not installed. Install with: pip install torch"}

    import torch
    import torch.nn as nn
    import torch.optim as optim
    from torch.utils.data import DataLoader, TensorDataset
    from sklearn.preprocessing import StandardScaler
    import joblib

    X, y = _prepare_sequences(ohlcv)
    if X is None or y is None:
        return {"error": f"Insufficient data: need {SEQUENCE_LENGTH + 10}+ candles"}

    n_samples, seq_len, n_features = X.shape
    logger.info("Prepared %d sequences (seq_len=%d, features=%d)", n_samples, seq_len, n_features)

    # Normalise features per-channel using StandardScaler
    scaler = StandardScaler()
    flat = X.reshape(-1, n_features)
    scaled = scaler.fit_transform(flat)
    X_scaled = scaled.reshape(n_samples, seq_len, n_features)

    # Split into train/validation
    split = int(n_samples * 0.8)
    X_train, X_val = X_scaled[:split], X_scaled[split:]
    y_train, y_val = y[:split], y[split:]

    train_loader = DataLoader(
        TensorDataset(torch.tensor(X_train), torch.tensor(y_train)),
        batch_size=batch_size,
        shuffle=True,
    )
    val_loader = DataLoader(
        TensorDataset(torch.tensor(X_val), torch.tensor(y_val)),
        batch_size=batch_size,
    )

    # Build model using factory function (avoids torch.nn.Module at module level)
    from lstm_model import _create_lstm_model

    model = _create_lstm_model(
        input_size=n_features,
        hidden_size=64,
        num_layers=2,
        num_classes=5,
    )

    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    scheduler = optim.lr_scheduler.ReduceLROnPlateau(optimizer, patience=5, factor=0.5)

    best_val_loss = float("inf")
    patience_counter = 0
    early_stop_patience = 10

    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        for batch_X, batch_y in train_loader:
            optimizer.zero_grad()
            outputs = model(batch_X)
            loss = criterion(outputs, batch_y)
            loss.backward()
            torch.nn.utils.clip_grad_norm_(model.parameters(), 1.0)
            optimizer.step()
            train_loss += loss.item()

        model.eval()
        val_loss = 0.0
        correct = 0
        total = 0
        with torch.no_grad():
            for batch_X, batch_y in val_loader:
                outputs = model(batch_X)
                loss = criterion(outputs, batch_y)
                val_loss += loss.item()
                _, predicted = torch.max(outputs, 1)
                total += batch_y.size(0)
                correct += (predicted == batch_y).sum().item()

        val_loss /= len(val_loader)
        accuracy = correct / total if total > 0 else 0
        scheduler.step(val_loss)

        if (epoch + 1) % 10 == 0:
            logger.info("Epoch %d/%d — train_loss=%.4f val_loss=%.4f accuracy=%.4f",
                        epoch + 1, epochs, train_loss / len(train_loader), val_loss, accuracy)

        # Early stopping
        if val_loss < best_val_loss:
            best_val_loss = val_loss
            patience_counter = 0
            torch.save(model.state_dict(), save_path)
        else:
            patience_counter += 1
            if patience_counter >= early_stop_patience:
                logger.info("Early stopping at epoch %d", epoch + 1)
                break

    # Save scaler
    os.makedirs(MODEL_DIR, exist_ok=True)
    joblib.dump(scaler, os.path.join(MODEL_DIR, "lstm_scaler.pkl"))

    # Save config
    config = {
        "input_size": n_features,
        "hidden_size": 64,
        "num_layers": 2,
        "sequence_length": SEQUENCE_LENGTH,
    }
    with open(os.path.join(MODEL_DIR, "lstm_config.json"), "w") as f:
        json.dump(config, f)

    # Compute final validation accuracy using tensors directly (not exhausted loader)
    model.eval()
    with torch.no_grad():
        outputs = model(torch.tensor(X_val))
        _, predicted = torch.max(outputs, 1)
        correct = (predicted == torch.tensor(y_val)).sum().item()
        total = len(y_val)

    final_accuracy = correct / total if total > 0 else 0

    logger.info("LSTM training complete. Validation accuracy: %.4f", final_accuracy)

    return {
        "status": "success",
        "accuracy": round(final_accuracy, 4),
        "epochs_trained": epoch + 1,
        "samples": n_samples,
        "val_samples": len(y_val),
        "features": n_features,
        "saved_to": save_path,
    }
