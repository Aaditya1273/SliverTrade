"""
SilverTrade — Binance Data Service
===================================
Lightweight Flask server that proxies the free Binance public klines API,
serving the same /api/v1/history format that Trade_Strategies expects.

No API key required — Binance klines are public.
Runs on port 5000.

Endpoints:
  POST /api/v1/history  — OHLCV data for backtesting & training
  POST /api/v1/ping     — Connectivity check
  GET  /api/v1/health   — Service health
  GET  /                — Status
"""

import json
import logging
import os
import time
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests
from flask import Flask, jsonify, request

logging.basicConfig(level=logging.INFO, format="[%(asctime)s] %(levelname)s: %(message)s")
logger = logging.getLogger("binance-data-service")

app = Flask(__name__)

BINANCE_BASE = "https://api.binance.com"
# Map Trade_Strategies exchange names to Binance quote currencies
EXCHANGE_MAP = {
    "CRYPTO": "USDT",
    "BINANCE": "USDT",
    "BTC": "BTC",
}
# Rate limit: 1200 requests per minute for public API
_last_request_time = 0.0
_MIN_INTERVAL = 0.05  # 50ms between calls


def _rate_limit():
    global _last_request_time
    now = time.monotonic()
    elapsed = now - _last_request_time
    if elapsed < _MIN_INTERVAL:
        time.sleep(_MIN_INTERVAL - elapsed)
    _last_request_time = time.monotonic()


def _normalize_symbol(symbol: str, exchange: str) -> str:
    """Normalize 'BTC/USDT' → 'BTCUSDT' for Binance."""
    quote = EXCHANGE_MAP.get(exchange.upper(), "USDT")
    s = symbol.upper().replace("/", "").replace("-", "")
    if not s.endswith(quote):
        s += quote
    return s


def _normalize_interval(interval: str) -> str:
    """Normalize interval to Binance format."""
    mapping = {
        "1m": "1m", "3m": "3m", "5m": "5m", "15m": "15m",
        "30m": "30m", "1h": "1h", "2h": "2h", "4h": "4h",
        "6h": "6h", "8h": "8h", "12h": "12h", "1d": "1d",
        "3d": "3d", "1w": "1w", "1M": "1M",
    }
    return mapping.get(interval, "1h")


def _fetch_klines(
    symbol: str, interval: str, start_time: Optional[int] = None, end_time: Optional[int] = None, limit: int = 1000
) -> List[Dict[str, Any]]:
    """Fetch klines from Binance public API."""
    params = {"symbol": symbol, "interval": interval, "limit": min(limit, 1000)}
    if start_time:
        params["startTime"] = int(start_time * 1000)  # Binance uses ms
    if end_time:
        params["endTime"] = int(end_time * 1000)

    _rate_limit()
    url = f"{BINANCE_BASE}/api/v3/klines"
    resp = requests.get(url, params=params, timeout=30)
    resp.raise_for_status()
    data = resp.json()

    candles = []
    for k in data:
        candles.append({
            "timestamp": k[0] // 1000,  # Convert ms → s
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
            "oi": 0,  # Binance doesn't provide OI in klines
        })
    return candles


# ── Endpoints ────────────────────────────────────────────────────────

@app.route("/api/v1/history", methods=["POST"])
def history():
    """Fetch OHLCV data from Binance.

    Request body:
      - symbol: Trading pair (e.g. BTC/USDT)
      - exchange: Exchange (CRYPTO, BINANCE)
      - interval: Candle interval (15m, 1h, 4h, 1d, etc.)
      - start_date: Start date YYYY-MM-DD
      - end_date: End date YYYY-MM-DD
    """
    data = request.get_json(silent=True) or {}
    symbol = data.get("symbol", "BTC/USDT")
    exchange = data.get("exchange", "CRYPTO")
    interval = data.get("interval", "15m")
    start_date = data.get("start_date", "")
    end_date = data.get("end_date", "")

    binance_symbol = _normalize_symbol(symbol, exchange)
    binance_interval = _normalize_interval(interval)

    try:
        # Convert dates to timestamps
        start_ts = None
        end_ts = None
        if start_date:
            dt = datetime.strptime(start_date, "%Y-%m-%d")
            start_ts = int(dt.replace(tzinfo=timezone.utc).timestamp())
        if end_date:
            dt = datetime.strptime(end_date, "%Y-%m-%d")
            # End of day
            dt = dt.replace(hour=23, minute=59, second=59, tzinfo=timezone.utc)
            end_ts = int(dt.timestamp())

        # Fetch in chunks if needed (Binance max 1000 per call)
        all_candles = []
        current_start = start_ts
        fetch_limit = 1000

        while True:
            candles = _fetch_klines(
                binance_symbol, binance_interval,
                start_time=current_start, end_time=end_ts,
                limit=fetch_limit,
            )
            if not candles:
                break
            all_candles.extend(candles)

            if len(candles) < fetch_limit:
                break

            # Last candle's time + 1 interval = next start
            last_time = candles[-1]["timestamp"]
            # Estimate next start (add interval in seconds)
            interval_seconds = {"1m": 60, "3m": 180, "5m": 300, "15m": 900,
                                "30m": 1800, "1h": 3600, "2h": 7200, "4h": 14400,
                                "6h": 21600, "8h": 28800, "12h": 43200,
                                "1d": 86400, "3d": 259200, "1w": 604800, "1M": 2592000}
            secs = interval_seconds.get(binance_interval, 3600)
            current_start = last_time + secs

            if end_ts and current_start > end_ts:
                break

        return jsonify({"status": "success", "data": all_candles})

    except requests.exceptions.HTTPError as e:
        logger.error(f"Binance API error: {e}")
        return jsonify({"status": "error", "message": f"Binance API error: {e.response.text}"}), 502
    except Exception as e:
        logger.exception(f"History error: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@app.route("/api/v1/ping", methods=["GET", "POST"])
def ping():
    """Connectivity check — verify Binance API is reachable."""
    try:
        _rate_limit()
        resp = requests.get(f"{BINANCE_BASE}/api/v3/ping", timeout=10)
        binance_ok = resp.status_code == 200
        return jsonify({
            "status": "success",
            "message": "Binance data service is running",
            "binance_api": "connected" if binance_ok else "unreachable",
        })
    except Exception:
        return jsonify({
            "status": "success",
            "message": "Binance data service is running",
            "binance_api": "unreachable",
        })


@app.route("/api/v1/health", methods=["GET"])
def health():
    """Service health check."""
    try:
        _rate_limit()
        resp = requests.get(f"{BINANCE_BASE}/api/v3/ping", timeout=10)
        binance_ok = resp.status_code == 200
    except Exception:
        binance_ok = False

    return jsonify({
        "status": "online",
        "service": "SilverTrade Binance Data Service",
        "version": "1.0.0",
        "binance_api": "connected" if binance_ok else "unreachable",
    })


@app.route("/")
def status():
    return jsonify({
        "status": "online",
        "service": "SilverTrade Binance Data Service",
        "endpoints": {
            "history": "POST /api/v1/history",
            "ping": "GET/POST /api/v1/ping",
            "health": "GET /api/v1/health",
        },
    })


if __name__ == "__main__":
    port = int(os.getenv("PORT", 5000))
    logger.info(f"Starting Binance Data Service on port {port}")
    app.run(host="0.0.0.0", port=port, debug=False)
