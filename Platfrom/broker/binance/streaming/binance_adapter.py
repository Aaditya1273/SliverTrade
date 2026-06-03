"""
binance_adapter.py

SilverTrade WebSocket adapter for Binance.

Streams used:
  <symbol>@ticker      — Real-time ticker (LTP, volume, OHLC, bid/ask)
  <symbol>@bookTicker  — Best bid/ask (quote mode)
  <symbol>@depth20     — 20-level order book (depth mode)

Authentication:
  Binance market data streams do NOT require authentication.
  Account-specific data (orders, trades) is not available via WebSocket
  in market data streams — use REST API for that.
"""

import json
import logging
import os
import threading
import time
from typing import Any

from broker.binance.streaming.binance_mapping import (
    BinanceCapabilityRegistry,
    BinanceExchangeMapper,
    BinanceModeMapper,
)
from broker.binance.streaming.websocket_client import BinanceWebSocket
from database.auth_db import get_auth_token
from database.token_db import get_br_symbol

import sys
import os as _os
sys.path.append(_os.path.join(_os.path.dirname(__file__), "../../../"))

from websocket_proxy.base_adapter import BaseBrokerWebSocketAdapter
from websocket_proxy.mapping import SymbolMapper


class BinanceWebSocketAdapter(BaseBrokerWebSocketAdapter):
    """Binance-specific implementation of the BaseBrokerWebSocketAdapter."""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("binance_websocket_adapter")
        self.ws_client = None
        self.user_id = None
        self.broker_name = "binance"
        self.running = False
        self._lock = threading.Lock()
        self.last_values: dict[str, dict] = {}

    # ── BaseBrokerWebSocketAdapter interface ──────────────────────────────────

    def initialize(
        self,
        broker_name: str,
        user_id: str,
        auth_data: dict | None = None,
    ) -> None:
        """
        Fetch credentials and build the BinanceWebSocket client.

        Binance market data WebSocket does NOT require authentication,
        but we keep the pattern for interface compatibility.
        """
        self.user_id = user_id
        self.broker_name = broker_name

        self.ws_client = BinanceWebSocket(
            on_message=self._on_data,
            on_open=self._on_open,
            on_error=self._on_error,
            on_close=self._on_close,
            max_retry_attempt=5,
            retry_delay=5,
            retry_multiplier=2,
        )

        self.running = True
        self.logger.info("BinanceWebSocketAdapter initialised for user %s", user_id)

    def connect(self) -> None:
        """Spin up the WebSocket connection in a daemon thread."""
        if not self.ws_client:
            self.logger.error("Call initialize() before connect()")
            return
        threading.Thread(target=self.ws_client.connect, daemon=True).start()

    def disconnect(self) -> None:
        """Close connection and clean up ZeroMQ resources."""
        self.running = False
        if self.ws_client:
            self.ws_client.close_connection()
        self.cleanup_zmq()

    def subscribe(
        self,
        symbol: str,
        exchange: str,
        mode: int = 2,
        depth_level: int = 1,
    ) -> dict[str, Any]:
        """
        Subscribe to market data for a single symbol.

        Modes:
          1 — LTP         → <symbol>@ticker
          2 — Quote       → <symbol>@bookTicker
          3 — Depth       → <symbol>@depth20
        """
        if not BinanceCapabilityRegistry.supports_mode(mode):
            return self._create_error_response(
                "INVALID_MODE",
                f"Mode {mode} not supported by Binance. Supported: {BinanceCapabilityRegistry.subscription_modes}",
            )

        token_info = SymbolMapper.get_token_from_symbol(symbol, exchange)
        if not token_info:
            return self._create_error_response(
                "SYMBOL_NOT_FOUND", f"{symbol} not found for exchange {exchange}"
            )

        br_symbol = get_br_symbol(symbol, exchange) or symbol
        stream = BinanceModeMapper.get_stream(mode)
        stream_name = f"{br_symbol.lower()}@{stream}"
        corr_id = f"{symbol}_{exchange}_{mode}"

        with self._lock:
            self.subscriptions[corr_id] = {
                "symbol":     symbol,
                "exchange":   exchange,
                "br_symbol":  br_symbol,
                "mode":       mode,
                "stream":     stream,
                "depth_level": depth_level,
                "stream_name": stream_name,
            }

        if self.ws_client:
            try:
                self.ws_client.subscribe([stream_name])
                self.logger.info("Subscribed: %s.%s mode=%s stream=%s", symbol, exchange, mode, stream_name)
            except Exception as exc:
                self.logger.error("subscribe error %s.%s: %s", symbol, exchange, exc)
                return self._create_error_response("SUBSCRIPTION_ERROR", str(exc))

        return self._create_success_response(
            f"Subscription requested for {symbol}.{exchange}",
            symbol=symbol, exchange=exchange, mode=mode, stream=stream_name,
        )

    def unsubscribe(self, symbol: str, exchange: str, mode: int = 2) -> dict[str, Any]:
        """Unsubscribe from market data for a symbol."""
        stream = BinanceModeMapper.get_stream(mode)
        corr_id = f"{symbol}_{exchange}_{mode}"

        should_disconnect = False
        stream_name = None

        with self._lock:
            stored = self.subscriptions.pop(corr_id, None)
            br_symbol = (stored or {}).get("br_symbol") or symbol
            stream_name = (stored or {}).get("stream_name") or f"{br_symbol.lower()}@{stream}"

            remaining = list(self.subscriptions.values())
            remaining_for_stream = [s for s in remaining if s.get("stream_name") == stream_name]

            cache_key = f"{symbol}_{exchange}"
            if not any(s.get("symbol") == symbol and s.get("exchange") == exchange for s in remaining):
                self.last_values.pop(cache_key, None)

            if not remaining:
                should_disconnect = True

        if not should_disconnect and not remaining_for_stream and self.ws_client:
            # No more subscribers for this stream — unsubscribe
            try:
                self.ws_client.unsubscribe([stream_name])
            except Exception as exc:
                self.logger.error("unsubscribe error %s.%s: %s", symbol, exchange, exc)

        if should_disconnect:
            self.logger.info("No subscriptions remaining — disconnecting.")
            self.disconnect()

        return self._create_success_response(
            f"Unsubscribed from {symbol}.{exchange}", symbol=symbol, exchange=exchange, mode=mode
        )

    # ── internal callbacks ────────────────────────────────────────────────────

    def _on_open(self, wsapp) -> None:
        self.logger.info("BinanceWS connection opened")
        self.connected = True

    def _on_error(self, wsapp, error) -> None:
        self.logger.error("BinanceWS error: %s", error)

    def _on_close(self, wsapp) -> None:
        self.logger.info("BinanceWS closed")
        self.connected = False

    def _on_data(self, wsapp, msg: dict) -> None:
        """
        Route incoming messages through normalisers.

        Combined streams message format:
            { "stream": "btcusdt@ticker", "data": { ... } }

        Binance ticker data shape:
            { "e": "24hrTicker", "E": 123456789, "s": "BTCUSDT",
              "c": "67000.00", "o": "66000.00", "h": "68000.00",
              "l": "65000.00", "v": "1234.567", "q": "82877123.45",
              "b": "66999.99", "a": "67000.01" }

        Binance bookTicker data shape:
            { "u": 12345, "s": "BTCUSDT", "b": "66999.99", "B": "1.500",
              "a": "67000.01", "A": "2.300" }

        Binance depth20 data shape:
            { "lastUpdateId": 12345, "bids": [["price", "qty"], ...],
              "asks": [["price", "qty"], ...] }
        """
        try:
            stream_name = msg.get("stream", "")
            data = msg.get("data", {})
            symbol = data.get("s", "").upper() if isinstance(data, dict) else ""

            if not stream_name or not symbol:
                return

            # Determine stream type from the name
            if "@ticker" in stream_name:
                self._handle_ticker(data, stream_name, symbol)
            elif "@bookTicker" in stream_name:
                self._handle_book_ticker(data, stream_name, symbol)
            elif "@depth" in stream_name:
                self._handle_depth(data, stream_name, symbol)

        except Exception as exc:
            self.logger.error("_on_data error: %s", exc, exc_info=True)

    def _handle_ticker(self, data: dict, stream_name: str, symbol: str) -> None:
        """Handle @ticker stream data."""
        subscriptions = self._find_subscriptions_by_stream(stream_name)
        if not subscriptions:
            return

        base_data = {
            "ltp":           float(data.get("c", 0)),
            "open":          float(data.get("o", 0)),
            "high":          float(data.get("h", 0)),
            "low":           float(data.get("l", 0)),
            "close":         float(data.get("c", 0)),
            "volume":        float(data.get("v", 0)),
            "oi":            0.0,
            "bid_price":     float(data.get("b", 0)),
            "ask_price":     float(data.get("a", 0)),
            "bid_qty":       float(data.get("B", 0)),
            "ask_qty":       float(data.get("A", 0)),
            "average_price": 0,
            "oi_change":     0,
        }

        ts = int(time.time() * 1000)
        for subscription in subscriptions:
            market_data = dict(base_data)
            market_data.update({
                "symbol":    subscription["symbol"],
                "exchange":  subscription["exchange"],
                "mode":      subscription["mode"],
                "timestamp": ts,
            })
            topic = f"{subscription['exchange']}_{subscription['symbol']}_LTP"
            self.publish_market_data(topic, market_data)

    def _handle_book_ticker(self, data: dict, stream_name: str, symbol: str) -> None:
        """Handle @bookTicker stream data."""
        subscriptions = self._find_subscriptions_by_stream(stream_name)
        if not subscriptions:
            return

        base_data = {
            "ltp":           0.0,
            "bid_price":     float(data.get("b", 0)),
            "ask_price":     float(data.get("a", 0)),
            "bid_qty":       float(data.get("B", 0)),
            "ask_qty":       float(data.get("A", 0)),
        }

        ts = int(time.time() * 1000)
        for subscription in subscriptions:
            market_data = dict(base_data)
            market_data.update({
                "symbol":    subscription["symbol"],
                "exchange":  subscription["exchange"],
                "mode":      subscription["mode"],
                "timestamp": ts,
            })
            topic = f"{subscription['exchange']}_{subscription['symbol']}_QUOTE"
            self.publish_market_data(topic, market_data)

    def _handle_depth(self, data: dict, stream_name: str, symbol: str) -> None:
        """Handle @depth stream data."""
        subscriptions = self._find_subscriptions_by_stream(stream_name)
        if not subscriptions:
            return

        bids_raw = data.get("bids", [])
        asks_raw = data.get("asks", [])

        def _parse_levels(levels, n=5):
            out = []
            for lvl in levels[:n]:
                if isinstance(lvl, list) and len(lvl) >= 2:
                    out.append({"price": float(lvl[0]), "quantity": float(lvl[1])})
            while len(out) < n:
                out.append({"price": 0.0, "quantity": 0})
            return out

        bids = _parse_levels(bids_raw)
        asks = _parse_levels(asks_raw)

        base_data = {
            "depth": {"buy": bids, "sell": asks},
            "totalbuyqty": sum(lvl["quantity"] for lvl in bids),
            "totalsellqty": sum(lvl["quantity"] for lvl in asks),
            "ltp": 0,
        }

        ts = int(time.time() * 1000)
        for subscription in subscriptions:
            market_data = dict(base_data)
            market_data.update({
                "symbol":    subscription["symbol"],
                "exchange":  subscription["exchange"],
                "mode":      subscription["mode"],
                "timestamp": ts,
            })
            topic = f"{subscription['exchange']}_{subscription['symbol']}_DEPTH"
            self.publish_market_data(topic, market_data)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _find_subscriptions_by_stream(self, stream_name: str) -> list[dict]:
        """Return ALL subscriptions matching a stream name."""
        with self._lock:
            return [
                sub for sub in self.subscriptions.values()
                if sub.get("stream_name") == stream_name
            ]
