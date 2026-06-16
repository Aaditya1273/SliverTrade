"""
SilverTrade AI - Trade Strategies Application
==============================================
AI-powered trading decision engine that generates signals using a
3-model ensemble (rule-based TA, Random Forest, LSTM).

Phase 3 Endpoints:
  POST /api/v1/signal          - Generate a full AI signal
  POST /api/v1/decision        - Analyze provided indicator data
  GET  /api/v1/signals         - Paginated signal history
  GET  /api/v1/signals/<id>    - Single signal detail
  POST /api/v1/backtest        - Run backtest on historical data
  GET  /api/v1/backtests       - Recent backtest results
  GET  /api/v1/accuracy        - Signal accuracy statistics
  GET  /api/v1/missed-opportunities - Missed profit opportunities
  GET  /api/v1/health          - Service health
  GET  /                       - Status
"""

import json
import logging
import os
import uuid
from datetime import datetime, timedelta, timezone
from typing import Any, Dict, List, Optional

import requests
from flask import Flask, jsonify, request
from flask_cors import CORS

from strategy_engine import StrategyEngine

app = Flask(__name__)
CORS(app)

engine = StrategyEngine()
_initialised = False
_outcome_tracker = None

PLATFORM_HOST = os.getenv("SILVERTRADE_HOST", "http://platform:5000")
PLATFORM_API_KEY = os.getenv("SILVERTRADE_API_KEY", "")


def _ensure_initialised():
    """Lazy initialise database and background jobs on first request."""
    global _initialised, _outcome_tracker
    if not _initialised:
        try:
            from database import init_db
            init_db()
            from outcome_tracker import OutcomeTracker
            _outcome_tracker = OutcomeTracker()
            _initialised = True
            app.logger.info("Strategy Engine fully initialised")
        except Exception as e:
            app.logger.error("Initialisation error: %s", e)
        # Auto-train Random Forest if no model checkpoint exists
        _auto_train_if_needed()


# ── Auto-train ───────────────────────────────────────────────────────

def _auto_train_if_needed():
    """Auto-train RF model on first boot if no checkpoint exists.

    Uses real OHLCV from Platform (if available) or falls back to
    synthetic data so the engine is never rule-only on first launch.
    Runs in the background so startup is not delayed.
    """
    import os
    import threading

    MODEL_PATH = os.path.join(os.path.dirname(__file__), "ml", "models", "random_forest.pkl")
    if os.path.exists(MODEL_PATH):
        return  # Already trained

    def _train():
        app.logger.info("[auto-train] No RF model found — training now in background...")
        try:
            # Try real data first
            ohlcv = None
            if PLATFORM_API_KEY:
                try:
                    ohlcv = fetch_historical_data(
                        "BTC/USDT", "CRYPTO", "15m",
                        (datetime.now(timezone.utc).replace(day=1) - timedelta(days=365)).strftime("%Y-%m-%d"),
                        datetime.now(timezone.utc).strftime("%Y-%m-%d"),
                    )
                except Exception:
                    pass

            # Fallback to 2 years of synthetic data
            if not ohlcv or len(ohlcv) < 200:
                app.logger.info("[auto-train] Using synthetic data (no API key or broker not connected)")
                ohlcv = []
                import random
                price = 50000.0
                ts = int(datetime.now(timezone.utc).timestamp()) - 365 * 24 * 3600
                for i in range(2000):  # ~2000 15m candles ≈ 20 days
                    change = random.gauss(0, price * 0.003)
                    close = max(price + change, 100)
                    high = close + abs(random.gauss(0, close * 0.002))
                    low = close - abs(random.gauss(0, close * 0.002))
                    ohlcv.append({
                        "time": ts + i * 900,
                        "open": round(price, 2),
                        "high": round(high, 2),
                        "low": round(low, 2),
                        "close": round(close, 2),
                        "volume": round(random.uniform(100, 10000), 2),
                    })
                    price = close

            from ml.random_forest_model import train_random_forest
            result = train_random_forest(ohlcv)
            if "error" not in result:
                # Reload the engine so it picks up the newly trained model
                engine._initialise_models()
                app.logger.info(
                    "[auto-train] RF model trained: accuracy=%.3f samples=%d",
                    result.get("accuracy", 0),
                    result.get("samples", 0),
                )
            else:
                app.logger.warning("[auto-train] RF training failed: %s", result["error"])
        except Exception as e:
            app.logger.error("[auto-train] Unexpected error: %s", e)

    thread = threading.Thread(target=_train, daemon=True, name="auto-train-rf")
    thread.start()


# ── Helpers ──────────────────────────────────────────────────────────

def fetch_market_data(symbol: str, exchange: str = "CRYPTO") -> Optional[List[Dict[str, Any]]]:
    """Fetch OHLCV data from the Platform API for analysis.

    Fetches 7 days of 15m data to ensure we have enough candles
    (>= 50 required) for indicator calculations and ML predictions.
    """
    try:
        url = f"{PLATFORM_HOST}/api/v1/history"
        now = datetime.now(timezone.utc)
        start = now - timedelta(days=7)
        payload = {
            "apikey": PLATFORM_API_KEY,
            "symbol": symbol,
            "exchange": exchange,
            "interval": "15m",
            "start_date": start.strftime("%Y-%m-%d"),
            "end_date": now.strftime("%Y-%m-%d"),
        }
        response = requests.post(url, json=payload, timeout=30)
        data = response.json()

        if data.get("status") == "error":
            return None

        ohlcv_data = data.get("data")
        if not ohlcv_data:
            return None

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
        app.logger.error("Failed to fetch market data for %s: %s", symbol, e)
        return None


def fetch_historical_data(symbol: str, exchange: str, interval: str,
                          start_date: str, end_date: str) -> Optional[List[Dict[str, Any]]]:
    """Fetch historical OHLCV data with custom date range for backtesting."""
    try:
        url = f"{PLATFORM_HOST}/api/v1/history"
        payload = {
            "apikey": PLATFORM_API_KEY,
            "symbol": symbol,
            "exchange": exchange,
            "interval": interval,
            "start_date": start_date,
            "end_date": end_date,
        }
        response = requests.post(url, json=payload, timeout=120)
        data = response.json()

        if data.get("status") == "error":
            return None

        ohlcv_data = data.get("data")
        if not ohlcv_data:
            return None

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
        app.logger.error("Failed to fetch historical data: %s", e)
        return None


def generate_mock_ohlcv() -> List[Dict[str, Any]]:
    """Generate synthetic OHLCV data for demo when platform is unavailable."""
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


# ── Signal Generation ────────────────────────────────────────────────

@app.route("/api/v1/signal", methods=["POST"])
def generate_signal():
    """Fetch market data and generate a full AI signal with 3-model ensemble.

    Body:
      - symbol: Trading pair (default: BTC/USDT)
      - exchange: Exchange (default: CRYPTO)
    """
    _ensure_initialised()
    data = request.get_json(silent=True) or {}
    symbol = data.get("symbol", "BTC/USDT")
    exchange = data.get("exchange", "CRYPTO")

    ohlcv = fetch_market_data(symbol, exchange)
    using_mock = False
    if not ohlcv:
        ohlcv = generate_mock_ohlcv()
        using_mock = True

    try:
        signal = engine.analyze(symbol, ohlcv, exchange)
    except Exception as e:
        app.logger.error("Engine crashed in /signal: %s", e)
        return jsonify({"status": "error", "message": "Analysis engine error"}), 500

    if not signal:
        return jsonify({"status": "error", "message": "Insufficient data"}), 422

    signal["mock_data"] = using_mock
    signal["id"] = str(uuid.uuid4())[:8]

    # Persist to database
    try:
        from database import insert_signal, add_pending_outcome
        insert_signal(signal)
        # Schedule outcome evaluation (1 hour later)
        add_pending_outcome(signal, check_after_minutes=60)
    except Exception as e:
        app.logger.warning("Failed to persist signal: %s", e)

    return jsonify({"status": "success", "data": signal})


@app.route("/api/v1/decision", methods=["POST"])
def get_decision():
    """Analyze indicator data and return a trading decision."""
    _ensure_initialised()
    data = request.get_json(silent=True)
    if not data:
        return jsonify({"error": "No data provided"}), 400

    symbol = data.get("symbol", "BTC/USDT")
    ohlcv = data.get("ohlcv")

    if ohlcv:
        try:
            signal = engine.analyze(symbol, ohlcv)
        except Exception as e:
            app.logger.error("Engine crashed in /decision: %s", e)
            return jsonify({"status": "error", "message": "Analysis error"}), 500

        if signal:
            signal["id"] = str(uuid.uuid4())[:8]
            try:
                from database import insert_signal, add_pending_outcome
                insert_signal(signal)
                add_pending_outcome(signal, check_after_minutes=60)
            except Exception:
                pass
            return jsonify({"status": "success", "data": signal})

    return jsonify({"error": "No OHLCV data provided"}), 400


@app.route("/api/v1/signals", methods=["GET"])
def get_signals():
    """Get paginated signal history from database.

    Query params:
      - limit: max results (default 20, max 100)
      - offset: pagination offset (default 0)
    """
    _ensure_initialised()
    limit = min(int(request.args.get("limit", 20)), 100)
    offset = int(request.args.get("offset", 0))

    try:
        from database import get_signals
        signals = get_signals(limit=limit, offset=offset)
        return jsonify({
            "status": "success",
            "count": len(signals),
            "signals": signals,
        })
    except Exception as e:
        app.logger.error("Failed to fetch signals: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/v1/signals/<signal_id>", methods=["GET"])
def get_signal(signal_id: str):
    """Get a single signal by ID."""
    _ensure_initialised()
    try:
        from database import get_signal_by_id
        signal = get_signal_by_id(signal_id)
        if not signal:
            return jsonify({"status": "error", "message": "Signal not found"}), 404
        return jsonify({"status": "success", "data": signal})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/v1/signals/<signal_id>/mark-executed", methods=["POST"])
def mark_signal_executed(signal_id: str):
    """Mark a signal as executed with an order ID.

    Called by Platform's execute_signal endpoint after a successful
    broker order so the Strategy Engine can track which signals were
    acted on vs missed.
    """
    _ensure_initialised()
    try:
        data = request.get_json(silent=True) or {}
        order_id = data.get("order_id", "")

        from database import mark_signal_as_executed
        success = mark_signal_as_executed(signal_id, order_id)

        if success:
            return jsonify({"status": "success", "message": "Signal marked as executed"})
        # Signal not found — not an error, just log and return OK so execute_signal
        # doesn't fail on this non-critical step
        return jsonify({"status": "success", "message": "Signal not found (already expired or deleted)"})
    except Exception as e:
        app.logger.warning("Failed to mark signal as executed: %s", e)
        # Return 200 — this is non-critical and must not block order execution
        return jsonify({"status": "success", "message": "Non-critical: could not update signal"})


# ── Backtesting ──────────────────────────────────────────────────────

@app.route("/api/v1/backtest", methods=["POST"])
def run_backtest():
    """Run a backtest on historical data.

    Body:
      - symbol: Trading pair
      - exchange: Exchange name
      - interval: Candle interval (default: 15m)
      - start_date: Start date (YYYY-MM-DD)
      - end_date: End date (YYYY-MM-DD)
      - capital: Initial capital (default: 100000)
      - position_size_pct: % per trade (default: 10)
      - stop_loss_pct: Stop loss % (default: 2)
      - take_profit_pct: Take profit % (default: 5)
    """
    _ensure_initialised()
    data = request.get_json(silent=True) or {}

    symbol = data.get("symbol", "BTC/USDT")
    exchange = data.get("exchange", "CRYPTO")
    interval = data.get("interval", "15m")
    start_date = data.get("start_date", "")
    end_date = data.get("end_date", "")
    capital = float(data.get("capital", 100000))
    position_size_pct = float(data.get("position_size_pct", 10))
    stop_loss_pct = float(data.get("stop_loss_pct", 2))
    take_profit_pct = float(data.get("take_profit_pct", 5))

    if not start_date or not end_date:
        return jsonify({"status": "error", "message": "start_date and end_date required"}), 400

    # Fetch historical data
    ohlcv = fetch_historical_data(symbol, exchange, interval, start_date, end_date)
    if not ohlcv:
        return jsonify({"status": "error", "message": "No data returned from Platform API"}), 422

    # Run backtest
    try:
        from backtester import Backtester
        backtester = Backtester(engine)
        result = backtester.run(
            ohlcv=ohlcv,
            symbol=symbol,
            exchange=exchange,
            initial_capital=capital,
            position_size_pct=position_size_pct,
            stop_loss_pct=stop_loss_pct,
            take_profit_pct=take_profit_pct,
        )

        metrics = result.to_dict()

        # Save to DB
        try:
            from database import save_backtest_result
            bt_config = {
                "start_date": start_date,
                "end_date": end_date,
                "initial_capital": capital,
                "position_size_pct": position_size_pct,
                "stop_loss_pct": stop_loss_pct,
                "take_profit_pct": take_profit_pct,
            }
            save_backtest_result(symbol, exchange, interval, metrics, bt_config)
        except Exception as e:
            app.logger.warning("Failed to save backtest result: %s", e)

        return jsonify({
            "status": "success",
            "data": metrics,
        })

    except Exception as e:
        app.logger.error("Backtest failed: %s", e)
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/v1/backtests", methods=["GET"])
def get_backtests():
    """Get recent backtest results."""
    _ensure_initialised()
    try:
        from database import get_backtest_results
        results = get_backtest_results(limit=20)
        return jsonify({"status": "success", "data": results})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ── Accuracy & Missed Opportunities ──────────────────────────────────

@app.route("/api/v1/accuracy", methods=["GET"])
def get_accuracy():
    """Get signal accuracy statistics.

    Returns overall win rate, per-decision breakdown, per-symbol breakdown.
    """
    _ensure_initialised()
    try:
        from database import get_outcome_summary
        summary = get_outcome_summary()
        return jsonify({"status": "success", "data": summary})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/v1/user-accuracy", methods=["GET"])
def get_user_accuracy():
    """Get user-specific win rate (only executed signals).

    Returns win rate for signals the user actually executed.
    """
    _ensure_initialised()
    try:
        from database import get_executed_signals_with_outcomes
        executed = get_executed_signals_with_outcomes()
        if not executed:
            return jsonify({
                "status": "success",
                "data": {
                    "win_rate": None,
                    "trades_evaluated": 0,
                    "note": "No executed trades evaluated yet"
                }
            })
        
        wins = [s for s in executed if s.get("was_correct")]
        win_rate = len(wins) / len(executed)
        
        return jsonify({
            "status": "success",
            "data": {
                "win_rate": round(win_rate, 4),
                "trades_evaluated": len(executed),
                "note": "Requires 10+ evaluated trades" if len(executed) < 10 else None
            }
        })
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/v1/missed-opportunities", methods=["GET"])
def get_missed_opportunities():
    """Get missed profit opportunities.

    Query params:
      - days: lookback period (default: 7)
      - limit: max results (default: 50)
    """
    _ensure_initialised()
    days = int(request.args.get("days", 7))
    limit = min(int(request.args.get("limit", 50)), 100)

    try:
        from database import get_missed_opportunities
        result = get_missed_opportunities(days=days, limit=limit)
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ── Alert Rules ─────────────────────────────────────────────────────

@app.route("/api/v1/alert-rules", methods=["GET"])
def get_alert_rules():
    """Get user's alert rules."""
    _ensure_initialised()
    try:
        from database import get_alert_rules
        rules = get_alert_rules()
        return jsonify({"status": "success", "data": rules})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/v1/alert-rules", methods=["POST"])
def save_alert_rule():
    """Save or update an alert rule."""
    _ensure_initialised()
    try:
        data = request.get_json(silent=True) or {}
        from database import save_alert_rule
        rule_id = save_alert_rule(data)
        return jsonify({"status": "success", "data": {"id": rule_id}})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/v1/test-alert", methods=["POST"])
def test_alert():
    """Send a test notification to verify alert configuration."""
    _ensure_initialised()
    try:
        from alerts_engine import AlertsEngine
        engine = AlertsEngine()
        
        test_signal = {
            "id": "test-" + str(uuid.uuid4())[:8],
            "symbol": "BTC/USDT",
            "decision": "BUY",
            "confidence": 85,
            "price": 50000.0,
            "reasoning": "This is a test alert to verify your notification settings are working correctly.",
        }
        
        rules = [{"enabled": True, "min_confidence": 50, "symbols": [], "channels": ["browser"]}]
        for rule in rules:
            engine._send_notification(test_signal, rule)
        
        return jsonify({"status": "success", "message": "Test alert sent"})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ── Model Training ───────────────────────────────────────────────────

@app.route("/api/v1/train/rf", methods=["POST"])
def train_rf():
    """Train the Random Forest model on historical data.

    Body:
      - symbol: Trading pair (default: BTC/USDT)
      - exchange: Exchange (default: CRYPTO)
      - days: Days of history (default: 365)
    """
    _ensure_initialised()
    data = request.get_json(silent=True) or {}
    symbol = data.get("symbol", "BTC/USDT")
    exchange = data.get("exchange", "CRYPTO")
    days = int(data.get("days", 365))

    from datetime import timedelta
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    ohlcv = fetch_historical_data(
        symbol, exchange, "15m",
        start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"),
    )
    if not ohlcv:
        return jsonify({"status": "error", "message": "No data returned"}), 422

    try:
        from ml.random_forest_model import train_random_forest
        result = train_random_forest(ohlcv)
        if "error" in result:
            return jsonify({"status": "error", "message": result["error"]}), 500
        return jsonify({"status": "success", "data": result})
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/v1/train/lstm", methods=["POST"])
def train_lstm():
    """Train the LSTM model on historical data.

    Body:
      - symbol: Trading pair (default: BTC/USDT)
      - exchange: Exchange (default: CRYPTO)
      - days: Days of history (default: 365)
    """
    _ensure_initialised()
    data = request.get_json(silent=True) or {}
    symbol = data.get("symbol", "BTC/USDT")
    exchange = data.get("exchange", "CRYPTO")
    days = int(data.get("days", 365))

    from datetime import timedelta
    end = datetime.now(timezone.utc)
    start = end - timedelta(days=days)

    ohlcv = fetch_historical_data(
        symbol, exchange, "15m",
        start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d"),
    )
    if not ohlcv:
        return jsonify({"status": "error", "message": "No data returned"}), 422

    try:
        from ml.lstm_train import train_lstm
        result = train_lstm(ohlcv)
        if "error" in result:
            return jsonify({"status": "error", "message": result["error"]}), 500
        return jsonify({"status": "success", "data": result})
    except ImportError:
        return jsonify({"status": "error", "message": "PyTorch not installed. Install with: pip install torch"}), 500
    except Exception as e:
        return jsonify({"status": "error", "message": str(e)}), 500


# ── Health ───────────────────────────────────────────────────────────

@app.route("/api/v1/health", methods=["GET"])
def health_check():
    """Service health check."""
    platform_status = "unknown"
    try:
        r = requests.get(f"{PLATFORM_HOST}/api/v1/health", timeout=5)
        platform_status = "connected" if r.status_code == 200 else "unreachable"
    except Exception:
        platform_status = "unreachable"

    models_status = {
        "random_forest": "trained" if (engine._rf_model and engine._rf_model.is_trained) else "not_trained",
        "lstm": "trained" if (engine._lstm_model and engine._lstm_model.is_trained) else "not_trained",
        "llm_reasoning": "available" if (engine._reasoning_engine and engine._reasoning_engine.available) else "unavailable",
    }

    return jsonify({
        "status": "online",
        "service": "SilverTrade AI Strategy Engine",
        "version": engine.version,
        "model": engine.name,
        "platform": platform_status,
        "models": models_status,
    })


@app.route("/")
def status():
    return jsonify({
        "status": "online",
        "service": "SilverTrade AI Strategy Engine",
        "version": engine.version,
        "model": engine.name,
    })


if __name__ == "__main__":
    _ensure_initialised()
    port = int(os.getenv("STRATEGY_PORT", 5007))
    debug = os.getenv("FLASK_DEBUG", "False").lower() in ("true", "1", "t")
    app.logger.info("SilverTrade AI Strategy Engine starting on port %d", port)
    app.run(host="0.0.0.0", port=port, debug=debug)
