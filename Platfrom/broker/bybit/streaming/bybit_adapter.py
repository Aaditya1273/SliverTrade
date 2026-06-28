"""
bybit_adapter.py

SilverTrade WebSocket adapter for Bybit.

Topics used:
  tickers.{symbol}         — Real-time ticker (LTP, volume, OHLC, bid/ask)
  orderbook.50.{symbol}    — 50-level order book (depth mode)

Authentication:
  Bybit market data streams do NOT require authentication.
  Private streams (for account orders/positions) require auth, which is
  sent automatically by the BybitWebSocket when api_key/api_secret are set.
"""

import json
import logging
import os
import threading
import time
from typing import Any

from broker.bybit.streaming.bybit_mapping import (
    BybitCapabilityRegistry,
    BybitExchangeMapper,
    BybitModeMapper,
)
from broker.bybit.streaming.websocket_client import BybitWebSocket
from database.auth_db import get_auth_token
from database.token_db import get_br_symbol

import sys
import os as _os

sys.path.append(_os.path.join(_os.path.dirname(__file__), "../../../"))

from websocket_proxy.base_adapter import BaseBrokerWebSocketAdapter
from websocket_proxy.mapping import SymbolMapper


class BybitWebSocketAdapter(BaseBrokerWebSocketAdapter):
    """Bybit-specific implementation of the BaseBrokerWebSocketAdapter."""

    def __init__(self):
        super().__init__()
        self.logger = logging.getLogger("bybit_websocket_adapter")
        self.ws_client = None
        self.user_id = None
        self.broker_name = "bybit"
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
        """Initialise the WebSocket adapter with credentials."""
        self.user_id = user_id
        self.broker_name = broker_name

        api_key = None
        api_secret = None
        if auth_data:
            api_key = auth_data.get("api_key") or auth_data.get("access_token", "")
            api_secret = auth_data.get("api_secret", "")
        else:
            api_key = get_auth_token(user_id) or ""

        self.ws_client = BybitWebSocket(
            api_key=api_key or "",
            api_secret=api_secret or os.getenv("BROKER_API_SECRET", ""),
            on_message=self._on_data,
            on_open=self._on_open,
            on_error=self._on_error,
            on_close=self._on_close,
            max_retry_attempt=5,
            retry_delay=5,
            retry_multiplier=2,
        )

        self.running = True
        self.logger.info("BybitWebSocketAdapter initialised for user %s", user_id)

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
          1 — LTP         → tickers.{symbol}
          2 — Quote       → tickers.{symbol}
          3 — Depth       → orderbook.50.{symbol}
        """
        if not BybitCapabilityRegistry.supports_mode(mode):
            return self._create_error_response(
                "INVALID_MODE",
                f"Mode {mode} not supported by Bybit. Supported: {BybitCapabilityRegistry.subscription_modes}",
            )

        token_info = SymbolMapper.get_token_from_symbol(symbol, exchange)
        if not token_info:
            return self._create_error_response(
                "SYMBOL_NOT_FOUND", f"{symbol} not found for exchange {exchange}"
            )

        br_symbol = get_br_symbol(symbol, exchange) or symbol
        topic = BybitModeMapper.get_topic_for_symbol(br_symbol, mode)
        corr_id = f"{symbol}_{exchange}_{mode}"

        with self._lock:
            self.subscriptions[corr_id] = {
                "symbol": symbol,
                "exchange": exchange,
                "br_symbol": br_symbol,
                "mode": mode,
                "depth_level": depth_level,
                "topic": topic,
            }

        if self.ws_client:
            try:
                self.ws_client.subscribe([topic])
                self.logger.info(
                    "Subscribed: %s.%s mode=%s topic=%s", symbol, exchange, mode, topic
                )
            except Exception as exc:
                self.logger.error("subscribe error %s.%s: %s", symbol, exchange, exc)
                return self._create_error_response("SUBSCRIPTION_ERROR", str(exc))

        return self._create_success_response(
            f"Subscription requested for {symbol}.{exchange}",
            symbol=symbol,
            exchange=exchange,
            mode=mode,
            topic=topic,
        )

    def unsubscribe(self, symbol: str, exchange: str, mode: int = 2) -> dict[str, Any]:
        """Unsubscribe from market data for a symbol."""
        corr_id = f"{symbol}_{exchange}_{mode}"

        with self._lock:
            stored = self.subscriptions.pop(corr_id, None)
            br_symbol = (stored or {}).get("br_symbol") or symbol
            topic = (stored or {}).get("topic") or BybitModeMapper.get_topic_for_symbol(
                br_symbol, mode
            )

            remaining = list(self.subscriptions.values())
            remaining_for_topic = [s for s in remaining if s.get("topic") == topic]

            cache_key = f"{symbol}_{exchange}"
            if not any(
                s.get("symbol") == symbol and s.get("exchange") == exchange for s in remaining
            ):
                self.last_values.pop(cache_key, None)

            if not remaining:
                self.logger.info("No subscriptions remaining — disconnecting.")
                self.disconnect()
                return self._create_success_response(
                    f"Unsubscribed from {symbol}.{exchange}",
                    symbol=symbol,
                    exchange=exchange,
                    mode=mode,
                )

        if not remaining_for_topic and self.ws_client:
            self.ws_client.unsubscribe([topic])

        return self._create_success_response(
            f"Unsubscribed from {symbol}.{exchange}", symbol=symbol, exchange=exchange, mode=mode
        )

    # ── internal callbacks ────────────────────────────────────────────────────

    def _on_open(self, wsapp) -> None:
        self.logger.info("BybitWS connection opened")
        self.connected = True

    def _on_error(self, wsapp, error) -> None:
        self.logger.error("BybitWS error: %s", error)

    def _on_close(self, wsapp) -> None:
        self.logger.info("BybitWS closed")
        self.connected = False

    def _on_data(self, wsapp, msg: dict) -> None:
        """
        Route incoming messages through normalisers.

        Bybit ticker data shape:
            { "topic": "tickers.BTCUSDT", "type": "snapshot",
              "data": { "symbol": "BTCUSDT", "lastPrice": "67000", ... },
              "ts": 1671017382656 }

        Bybit orderbook data shape:
            { "topic": "orderbook.50.BTCUSDT", "type": "snapshot",
              "data": { "s": "BTCUSDT", "b": [["66999","1.5"],...], "a": [["67001","2.3"],...] },
              "ts": 1671017382656 }
        """
        try:
            topic = msg.get("topic", "")
            msg_type = msg.get("type", "")
            data = msg.get("data", {})
            ts = msg.get("ts", int(time.time() * 1000))

            if not topic or not data:
                return

            # Extract symbol from topic (format: "tickers.BTCUSDT" → "BTCUSDT")
            topic_parts = topic.split(".")
            if len(topic_parts) < 2:
                return
            raw_symbol = topic_parts[-1]  # Last part is always the symbol
            topic_name = topic_parts[0]

            if "ticker" in topic_name:
                self._handle_ticker(data, topic, raw_symbol, ts)
            elif "orderbook" in topic_name:
                self._handle_orderbook(data, topic, raw_symbol, ts)

        except Exception as exc:
            self.logger.error("_on_data error: %s", exc, exc_info=True)

    def _handle_ticker(self, data: dict, topic: str, raw_symbol: str, ts: int) -> None:
        """Handle tickers stream data."""
        subscriptions = self._find_subscriptions_by_topic(topic)
        if not subscriptions:
            return

        base_data = {
            "ltp": float(data.get("lastPrice", 0)),
            "open": float(data.get("open24h", 0)),
            "high": float(data.get("high24h", 0)),
            "low": float(data.get("low24h", 0)),
            "close": float(data.get("lastPrice", 0)),
            "volume": float(data.get("volume24h", 0)),
            "oi": float(data.get("openInterest", 0)),
            "bid_price": float(data.get("bid1Price", 0)),
            "ask_price": float(data.get("ask1Price", 0)),
            "bid_qty": float(data.get("bid1Size", 0)),
            "ask_qty": float(data.get("ask1Size", 0)),
            "average_price": 0,
            "oi_change": 0,
        }

        for subscription in subscriptions:
            market_data = dict(base_data)
            market_data.update(
                {
                    "symbol": subscription["symbol"],
                    "exchange": subscription["exchange"],
                    "mode": subscription["mode"],
                    "timestamp": ts,
                }
            )
            topic_key = f"{subscription['exchange']}_{subscription['symbol']}_LTP"
            self.publish_market_data(topic_key, market_data)

    def _handle_orderbook(self, data: dict, topic: str, raw_symbol: str, ts: int) -> None:
        """Handle orderbook stream data."""
        subscriptions = self._find_subscriptions_by_topic(topic)
        if not subscriptions:
            return

        bids_raw = data.get("b", [])
        asks_raw = data.get("a", [])

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

        for subscription in subscriptions:
            market_data = dict(base_data)
            market_data.update(
                {
                    "symbol": subscription["symbol"],
                    "exchange": subscription["exchange"],
                    "mode": subscription["mode"],
                    "timestamp": ts,
                }
            )
            topic_key = f"{subscription['exchange']}_{subscription['symbol']}_DEPTH"
            self.publish_market_data(topic_key, market_data)

    # ── helpers ───────────────────────────────────────────────────────────────

    def _find_subscriptions_by_topic(self, topic: str) -> list[dict]:
        """Return ALL subscriptions matching a topic."""
        with self._lock:
            return [sub for sub in self.subscriptions.values() if sub.get("topic") == topic]
