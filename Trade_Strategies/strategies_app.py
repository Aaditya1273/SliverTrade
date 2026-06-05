"""
SilverTrade AI - Trade Strategies Application
==============================================
AI-powered trading decision engine that analyzes market data using
technical indicators and generates real trading signals.

Endpoints:
  POST /api/v1/decision  - Generate a trade decision from indicators
  POST /api/v1/signal    - Fetch market data and generate a full signal
  GET  /                 - Service health check
"""

import json
import os
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

from strategy_engine import StrategyEngine

app = Flask(__name__)
CORS(app)

engine = StrategyEngine()

# In-memory signal history (production would use Redis/DB)
signal_history: List[Dict[str, Any]] = []
_signal_lock = threading.Lock()


PLATFORM_HOST = os.getenv("SILVERTRADE_HOST", "http://platform:5000")
PLATFORM_API_KEY = os.getenv("SILVERTRADE_API_KEY", "")


def fetch_market_data(symbol: str, exchange: str = "CRYPTO") -> Optional[List[Dict[str, Any]]]:
    """Fetch OHLCV data from the SilverTrade Platform API for analysis."""
    try:
        url = f"{PLATFORM_HOST}/api/v1/history"
        payload = {
            "apikey": PLATFORM_API_KEY,
            "symbol": symbol,
            "exchange": exchange,
            "interval": "15m",
            "start_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
            "end_date": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        }
        response = requests.post(url, json=payload, timeout=30)
        data = response.json()

        if data.get("status") == "error":
            return None

        ohlcv_data = data.get("data")
        if not ohlcv_data:
            return None

        # Normalize to the format our engine expects
        candles = []
        for row in ohlcv_data:
            candles.append({
                "time": row.get("timestamp", 0),
                "open": float(row.get("open", 0)),
                "high": float(row.get("high", 0)),
                "low": float(row.get("low", 0)),
                "close": float(row.get("close", 0)),
                "volume": float(row.get("volume", 0)),
            })
        return candles

    except Exception as e:
        app.logger.error(f"Failed to fetch market data for {symbol}: {e}")
        return None


def generate_mock_ohlcv() -> List[Dict[str, Any]]:
    """Generate synthetic OHLCV data for demo/testing when platform is unavailable."""
    import random
    base_price = 50000
    candles = []
    for i in range(100):
        change = random.gauss(0, 100)
        close = base_price + change
        high = close + abs(random.gauss(0, 50))
        low = close - abs(random.gauss(0, 50))
        open_price = base_price + random.gauss(0, 50)
        candles.append({
            "time": int(datetime.now(timezone.utc).timestamp()) - (100 - i) * 900,
            "open": round(open_price, 2),
            "high": round(high, 2),
            "low": round(low, 2),
            "close": round(close, 2),
            "volume": round(random.uniform(100, 10000), 2),
        })
        base_price = close
    return candles


def get_mock_indicator_data(symbol: str) -> Dict[str, Any]:
    """Generate mock indicator data for demo purposes."""
    import random
    return {
        "rsi": random.uniform(25, 75),
        "ema_9": random.uniform(48000, 52000),
        "ema_21": random.uniform(47500, 51500),
        "macd": random.uniform(-200, 200),
        "signal": random.uniform(-150, 150),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.route("/api/v1/decision", methods=["POST"])
def get_decision():
    """Analyze indicator data and return a trading decision.

    Accepts indicator values in the request body and runs the strategy
    engine to produce a BUY/SELL/HOLD signal with confidence score.
    """
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No data provided"}), 400

    symbol = data.get("symbol", "BTC/USDT")
    indicators = data.get("indicators", {})

    # Try to use the strategy engine with real data first
    ohlcv = data.get("ohlcv")
    if ohlcv:
        try:
            signal = engine.analyze(symbol, ohlcv)
        except Exception as e:
            app.logger.error(f"StrategyEngine.analyze() crashed in /decision: {e}")
            return jsonify({"status": "error", "message": "Analysis engine error"}), 500

        if signal:
            with _signal_lock:
                signal_history.insert(0, signal)
            return jsonify({
                "status": "success",
                "data": signal,
            })

    # Fallback: use provided indicators or generate mock
    if indicators:
        decision = _predict_from_indicators(indicators)
        decision["symbol"] = symbol
        decision["timestamp"] = datetime.now(timezone.utc).isoformat()
        return jsonify({
            "status": "success",
            "data": decision,
        })

    return jsonify({"error": "No indicator data or OHLCV provided"}), 400


@app.route("/api/v1/signal", methods=["POST"])
def generate_signal():
    """Fetch market data and generate a full AI signal.

    Body parameters:
      - symbol: Trading pair (default: BTC/USDT)
      - exchange: Exchange name (default: CRYPTO)

    Fetches OHLCV data from the Platform API and runs the strategy engine.
    Falls back to mock data if platform is unavailable.
    """
    data = request.get_json(silent=True) or {}
    symbol = data.get("symbol", "BTC/USDT")
    exchange = data.get("exchange", "CRYPTO")

    # Try fetching real market data
    ohlcv = fetch_market_data(symbol, exchange)

    if not ohlcv:
        # Fallback to mock data for demo
        ohlcv = generate_mock_ohlcv()
        using_mock = True
    else:
        using_mock = False

    try:
        signal = engine.analyze(symbol, ohlcv, exchange)
    except Exception as e:
        app.logger.error(f"StrategyEngine.analyze() crashed in /signal: {e}")
        return jsonify({"status": "error", "message": "Analysis engine error"}), 500

    if not signal:
        return jsonify({"status": "error", "message": "Insufficient data for analysis"}), 422

    signal["mock_data"] = using_mock
    signal["id"] = str(uuid.uuid4())[:8]
    with _signal_lock:
        signal_history.insert(0, signal)

    return jsonify({
        "status": "success",
        "data": signal,
    })


@app.route("/api/v1/signals", methods=["GET"])
def get_signals():
    """Get recent signal history."""
    limit = min(int(request.args.get("limit", 20)), 100)
    with _signal_lock:
        signals_snapshot = list(signal_history[:limit])
    return jsonify({
        "status": "success",
        "count": len(signals_snapshot),
        "signals": signals_snapshot,
    })


@app.route("/api/v1/health", methods=["GET"])
def health_check():
    """Service health check endpoint."""
    platform_status = "unknown"
    try:
        r = requests.get(f"{PLATFORM_HOST}/api/v1/health", timeout=5)
        platform_status = "connected" if r.status_code == 200 else "unreachable"
    except Exception:
        platform_status = "unreachable"

    return jsonify({
        "status": "online",
        "service": "SilverTrade AI Strategy Engine",
        "version": engine.version,
        "model": engine.name,
        "platform": platform_status,
        "signals_generated": len(signal_history),  # not critical, no lock needed
    })


@app.route("/")
def status():
    return jsonify({
        "status": "online",
        "service": "SilverTrade AI Strategy Engine",
        "version": engine.version,
        "model": engine.name,
    })


def _predict_from_indicators(indicator_data: dict) -> dict:
    """Generate a trading decision from indicator values using rule-based logic."""
    rsi = indicator_data.get("rsi", 50)
    ema_fast = indicator_data.get("ema_9", 0)
    ema_slow = indicator_data.get("ema_21", 0)

    confidence = 50
    decision = "HOLD"
    reasoning_parts = []

    # RSI Analysis
    if rsi < 30:
        confidence += 35
        reasoning_parts.append(f"RSI deeply oversold ({rsi:.1f})")
    elif rsi < 40:
        confidence += 15
        reasoning_parts.append(f"RSI approaching oversold ({rsi:.1f})")
    elif rsi > 70:
        confidence += 35
        reasoning_parts.append(f"RSI overbought ({rsi:.1f})")
    elif rsi > 60:
        confidence += 15
        reasoning_parts.append(f"RSI elevated ({rsi:.1f})")

    # EMA Trend Analysis
    if ema_fast > ema_slow:
        confidence += 15
        reasoning_parts.append("bullish EMA alignment")
    elif ema_fast < ema_slow:
        confidence -= 15
        reasoning_parts.append("bearish EMA alignment")

    # Determine final decision
    if (rsi < 30 and ema_fast > ema_slow) or (rsi < 40 and ema_fast > ema_slow):
        decision = "BUY"
        if not reasoning_parts:
            reasoning_parts.append("oversold bounce potential")
    elif (rsi > 70 and ema_fast < ema_slow) or (rsi > 60 and ema_fast < ema_slow):
        decision = "SELL"
        if not reasoning_parts:
            reasoning_parts.append("overbought reversal risk")
    elif ema_fast > ema_slow:
        decision = "BUY"
        reasoning_parts.append("moderate bullish trend")
    elif ema_fast < ema_slow:
        decision = "SELL"
        reasoning_parts.append("moderate bearish trend")
    else:
        reasoning_parts.append("neutral market conditions")

    confidence = max(min(confidence, 99), 10)

    return {
        "decision": decision,
        "confidence": round(confidence, 2),
        "reasoning": ". ".join(part.capitalize() for part in reasoning_parts) if reasoning_parts else "Neutral market conditions.",
    }


if __name__ == "__main__":
    port = int(os.getenv("STRATEGY_PORT", 5007))
    debug = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
    print(f"SilverTrade AI Strategy Engine starting on port {port}")
    app.run(host="0.0.0.0", port=port, debug=debug)
