"""
SilverTrade AI — Model Training Pipeline
==========================================
Trains both the Random Forest and LSTM models on historical OHLCV data.

Usage:
    # Fetch data and train both models
    python ml/train_models.py --symbol BTC/USDT --exchange CRYPTO --days 365

    # Train with pre-fetched data file
    python ml/train_models.py --data ohlcv_data.json

    # Train only Random Forest
    python ml/train_models.py --rf-only --data ohlcv_data.json

Requirements:
    - scikit-learn (for Random Forest)
    - PyTorch (for LSTM, optional — LSTM is skipped if not available)
"""

import argparse
import json
import logging
import os
import sys
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

# Add parent directory to path for imports
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger(__name__)


def fetch_ohlcv_from_platform(
    symbol: str,
    exchange: str,
    days: int = 365,
    interval: str = "15m",
    platform_host: str = "http://platform:5000",
    api_key: str = "",
) -> Optional[List[Dict[str, Any]]]:
    """Fetch historical OHLCV data from the Platform API for training."""
    import requests

    from datetime import timedelta

    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    try:
        url = f"{platform_host}/api/v1/history"
        payload = {
            "apikey": api_key,
            "symbol": symbol,
            "exchange": exchange,
            "interval": interval,
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": end.strftime("%Y-%m-%d"),
        }
        response = requests.post(url, json=payload, timeout=120)
        data = response.json()

        if data.get("status") == "error":
            logger.error("Platform API error: %s", data.get("message"))
            return None

        ohlcv = data.get("data")
        if not ohlcv:
            logger.error("No data returned from Platform API")
            return None

        logger.info("Fetched %d candles from Platform API", len(ohlcv))
        return ohlcv

    except Exception as e:
        logger.error("Failed to fetch data from Platform API: %s", e)
        return None


def main():
    parser = argparse.ArgumentParser(description="SilverTrade AI — Model Training Pipeline")
    parser.add_argument("--symbol", default="BTC/USDT", help="Trading symbol")
    parser.add_argument("--exchange", default="CRYPTO", help="Exchange name")
    parser.add_argument("--days", type=int, default=365, help="Days of history to fetch")
    parser.add_argument("--interval", default="15m", help="Candle interval")
    parser.add_argument("--data", help="Path to pre-fetched OHLCV JSON file")
    parser.add_argument("--rf-only", action="store_true", help="Train only Random Forest")
    parser.add_argument("--lstm-only", action="store_true", help="Train only LSTM")
    parser.add_argument("--verbose", "-v", action="store_true", help="Verbose output")
    args = parser.parse_args()

    if args.verbose:
        logging.getLogger().setLevel(logging.DEBUG)

    # Load data
    ohlcv: Optional[List[Dict[str, Any]]] = None

    if args.data:
        with open(args.data) as f:
            raw = json.load(f)
            ohlcv = raw.get("data") or raw.get("candles") or raw
        logger.info("Loaded %d candles from %s", len(ohlcv), args.data)
    else:
        ohlcv = fetch_ohlcv_from_platform(
            symbol=args.symbol,
            exchange=args.exchange,
            days=args.days,
            interval=args.interval,
        )

    if not ohlcv or len(ohlcv) < 100:
        logger.error("Insufficient data (%d candles). Need 100+ for training.", len(ohlcv) if ohlcv else 0)
        sys.exit(1)

    # Normalise: ensure sorted oldest → newest
    try:
        if ohlcv[0].get("time", 0) > ohlcv[-1].get("time", 0):
            ohlcv = list(reversed(ohlcv))
    except (IndexError, TypeError):
        pass

    results: Dict[str, Any] = {}

    # Train Random Forest
    if not args.lstm_only:
        logger.info("=" * 60)
        logger.info("Training Random Forest model...")
        try:
            from random_forest_model import train_random_forest

            rf_result = train_random_forest(ohlcv)
            results["random_forest"] = rf_result
            if "error" in rf_result:
                logger.error("Random Forest training failed: %s", rf_result["error"])
            else:
                logger.info("Random Forest trained: accuracy=%.3f", rf_result.get("accuracy", 0))
        except Exception as e:
            logger.exception("Random Forest training failed")
            results["random_forest"] = {"error": str(e)}

    # Train LSTM
    if not args.rf_only:
        logger.info("=" * 60)
        logger.info("Training LSTM model...")
        try:
            from lstm_model import LSTMSignalModel
            from lstm_train import train_lstm

            lstm_result = train_lstm(ohlcv)
            results["lstm"] = lstm_result
            if "error" in lstm_result:
                logger.error("LSTM training failed: %s", lstm_result["error"])
            else:
                logger.info("LSTM trained: accuracy=%.3f", lstm_result.get("accuracy", 0))
        except ImportError:
            logger.warning("PyTorch not installed — skipping LSTM training")
            results["lstm"] = {"status": "skipped", "reason": "PyTorch not installed"}
        except Exception as e:
            logger.exception("LSTM training failed")
            results["lstm"] = {"error": str(e)}

    # Save training report
    report_path = os.path.join(os.path.dirname(__file__), "models", "training_report.json")
    os.makedirs(os.path.dirname(report_path), exist_ok=True)
    with open(report_path, "w") as f:
        json.dump(results, f, indent=2)

    logger.info("=" * 60)
    logger.info("Training complete. Report saved to %s", report_path)
    logger.info(json.dumps(results, indent=2))


if __name__ == "__main__":
    main()
