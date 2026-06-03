"""
binance_websocket.py

Low-level WebSocket client for Binance real-time market data streams.

Endpoint : wss://stream.binance.com:9443/stream?streams=<stream1>/<stream2>/...
Protocol : JSON over secure WebSocket
Auth     : Binance market data streams do NOT require authentication.

Stream naming:
  <symbol>@ticker      – <symbol> is lowercase, e.g. "btcusdt@ticker"
  <symbol>@bookTicker  – Real-time best bid/ask
  <symbol>@depth20     – 20-level order book
  <symbol>@depth@100ms – Partial order book stream

Combined streams:
  /stream?streams=btcusdt@ticker/ethusdt@ticker

Incoming message format (combined streams):
  {
    "stream": "btcusdt@ticker",
    "data": { ... stream-specific payload ... }
  }

References:
  https://binance-docs.github.io/apidocs/spot/en/#websocket-market-streams
"""

import json
import logging
import ssl
import threading
import time
from urllib.parse import urlencode

import websocket

logger = logging.getLogger("binance_websocket")


class BinanceWebSocket:
    """
    Thin WebSocket client for Binance real-time market data streams.

    Usage:
        ws = BinanceWebSocket(on_message=cb, on_open=callback)
        ws.connect()
        ws.subscribe(["btcusdt@ticker", "ethusdt@ticker"])
        ...
        ws.close()
    """

    WS_URL = "wss://stream.binance.com:9443/stream"
    HEARTBEAT_INTERVAL = 30  # seconds between pings

    def __init__(
        self,
        on_message=None,
        on_error=None,
        on_open=None,
        on_close=None,
        max_retry_attempt: int = 5,
        retry_delay: int = 5,
        retry_multiplier: int = 2,
    ):
        self.on_message = on_message or (lambda ws, msg: None)
        self.on_error = on_error or (lambda ws, err: None)
        self.on_open = on_open or (lambda ws: None)
        self.on_close = on_close or (lambda ws: None)

        self.max_retry_attempt = max_retry_attempt
        self.retry_delay = retry_delay
        self.retry_multiplier = retry_multiplier

        self.wsapp = None
        self._lock = threading.Lock()
        self._connected = False
        self._stop_flag = False
        self._active_streams = []  # List of stream names for reconnect

    def _get_combined_url(self) -> str:
        """Build the combined stream URL from active streams."""
        if not self._active_streams:
            return self.WS_URL
        streams = "/".join(self._active_streams)
        return f"{self.WS_URL}?streams={streams}"

    def subscribe(self, streams: list[str]) -> None:
        """
        Subscribe to market data streams.

        Streams are added to the combined stream URL and the connection
        is re-established if already connected.

        Args:
            streams: List of stream names (e.g. ["btcusdt@ticker", "ethusdt@ticker"])
        """
        with self._lock:
            for s in streams:
                if s not in self._active_streams:
                    self._active_streams.append(s)

        if self._connected:
            logger.info(f"BinanceWS: reconnecting with {len(self._active_streams)} streams")
            self._reconnect()

    def unsubscribe(self, streams: list[str]) -> None:
        """Unsubscribe from streams and reconnect if connected."""
        with self._lock:
            for s in streams:
                if s in self._active_streams:
                    self._active_streams.remove(s)

        if self._connected:
            if self._active_streams:
                logger.info(f"BinanceWS: reconnecting with {len(self._active_streams)} streams")
                self._reconnect()
            else:
                logger.info("BinanceWS: no streams remaining, disconnecting")
                self.close_connection()

    def connect(self) -> None:
        """Start the WebSocket connection (blocking — run in a thread)."""
        self._stop_flag = False
        retry_attempts = 0
        delay = self.retry_delay

        while not self._stop_flag and retry_attempts <= self.max_retry_attempt:
            try:
                url = self._get_combined_url()
                logger.info(f"BinanceWS connecting to {url} (attempt {retry_attempts + 1})")
                self.wsapp = websocket.WebSocketApp(
                    url,
                    on_open=self._ws_on_open,
                    on_message=self._ws_on_message,
                    on_error=self._ws_on_error,
                    on_close=self._ws_on_close,
                )
                self.wsapp.run_forever(
                    sslopt={"cert_reqs": ssl.CERT_REQUIRED},
                    ping_interval=self.HEARTBEAT_INTERVAL,
                    ping_timeout=10,
                )
                if self._stop_flag:
                    break
                retry_attempts += 1
                logger.warning(f"BinanceWS disconnected; retry in {delay}s")
                time.sleep(delay)
                delay = min(delay * self.retry_multiplier, 60)

            except Exception as exc:
                logger.error(f"BinanceWS connect error: {exc}")
                retry_attempts += 1
                time.sleep(delay)
                delay = min(delay * self.retry_multiplier, 60)

        if retry_attempts > self.max_retry_attempt:
            logger.error("BinanceWS max reconnect attempts reached; giving up")

    def close_connection(self) -> None:
        """Cleanly stop the WebSocket."""
        self._stop_flag = True
        if self.wsapp:
            try:
                self.wsapp.close()
            except Exception:
                pass

    def _reconnect(self) -> None:
        """Force reconnect to pick up stream changes."""
        if self.wsapp:
            try:
                self.wsapp.close()
            except Exception:
                pass

    def _ws_on_open(self, wsapp) -> None:
        logger.info("BinanceWS connected")
        with self._lock:
            self._connected = True
        self.on_open(wsapp)

    def _ws_on_message(self, wsapp, raw) -> None:
        try:
            msg = json.loads(raw)
        except Exception:
            logger.debug(f"BinanceWS non-JSON message: {raw[:120]}")
            return

        # Combined streams format: {"stream": "...", "data": {...}}
        if isinstance(msg, dict) and "stream" in msg and "data" in msg:
            self.on_message(wsapp, msg)
        else:
            logger.debug(f"BinanceWS unexpected message format: {list(msg.keys()) if isinstance(msg, dict) else type(msg)}")

    def _ws_on_error(self, wsapp, error) -> None:
        logger.error(f"BinanceWS error: {error}")
        self.on_error(wsapp, error)

    def _ws_on_close(self, wsapp, *args) -> None:
        logger.info("BinanceWS closed")
        with self._lock:
            self._connected = False
        self.on_close(wsapp)
