"""
bybit_websocket.py

Low-level WebSocket client for Bybit real-time market data streams.

Endpoint : wss://stream.bybit.com/v5/public/spot
           wss://stream.bybit.com/v5/public/linear (for USDT perpetual)
Protocol : JSON over secure WebSocket
Auth     : Public market data streams do NOT require authentication.
           Private streams (order, position, wallet) require sending an auth message.

Subscription message format:
    { "op": "subscribe", "args": ["tickers.BTCUSDT", "orderbook.50.BTCUSDT"] }

Unsubscription:
    { "op": "unsubscribe", "args": ["tickers.BTCUSDT"] }

Auth message (for private streams):
    { "op": "auth", "args": ["API_KEY", "expires_timestamp", "signature"] }
    Signature: HMAC-SHA256(api_secret, "GET/realtime" + expires_timestamp)

Incoming message format:
    { "topic": "tickers.BTCUSDT", "type": "snapshot",
      "data": { ... stream-specific payload ... } },
      "ts": 1671017382656 }

Ticker data:
    { "symbol": "BTCUSDT", "lastPrice": "67000", "high24h": "68000",
      "low24h": "65000", "volume24h": "1234.56", "turnover24h": "82877123.45",
      "bid1Price": "66999.99", "ask1Price": "67000.01",
      "bid1Size": "1.5", "ask1Size": "2.3",
      "openInterest": "5000.12" }

Order book data:
    { "s": "BTCUSDT", "b": [["66999", "1.5"], ...], "a": [["67001", "2.3"], ...],
      "u": 12345, "seq": 67890 }

References:
  https://bybit-exchange.github.io/docs/v5/websocket/public/ticker
"""

import hashlib
import hmac
import json
import logging
import os
import ssl
import threading
import time

import websocket

logger = logging.getLogger("bybit_websocket")


class BybitWebSocket:
    """
    Thin WebSocket client for Bybit real-time market data streams.

    Usage:
        ws = BybitWebSocket(on_message=cb)
        ws.connect()
        ws.subscribe(["tickers.BTCUSDT", "orderbook.50.ETHUSDT"])
        ...
        ws.close()
    """

    WS_URL_SPOT = "wss://stream.bybit.com/v5/public/spot"
    WS_URL_LINEAR = "wss://stream.bybit.com/v5/public/linear"

    HEARTBEAT_INTERVAL = 20  # seconds between pings

    def __init__(
        self,
        api_key: str = "",
        api_secret: str = "",
        on_message=None,
        on_error=None,
        on_open=None,
        on_close=None,
        max_retry_attempt: int = 5,
        retry_delay: int = 5,
        retry_multiplier: int = 2,
        use_linear: bool = False,
    ):
        self.api_key = api_key
        self.api_secret = api_secret
        self.on_message = on_message or (lambda ws, msg: None)
        self.on_error = on_error or (lambda ws, err: None)
        self.on_open = on_open or (lambda ws: None)
        self.on_close = on_close or (lambda ws: None)

        self.max_retry_attempt = max_retry_attempt
        self.retry_delay = retry_delay
        self.retry_multiplier = retry_multiplier
        self.use_linear = use_linear

        self.ws_url = self.WS_URL_LINEAR if use_linear else self.WS_URL_SPOT
        self.wsapp = None
        self._lock = threading.Lock()
        self._connected = False
        self._stop_flag = False
        self._active_args = []  # List of topic args for reconnect

    def _build_auth_msg(self) -> str:
        """Build the authenticated auth message for private streams."""
        expires = str(int(time.time() * 1000) + 10000)  # 10s expiry
        signature = hmac.new(
            self.api_secret.encode("utf-8"),
            f"GET/realtime{expires}".encode("utf-8"),
            hashlib.sha256,
        ).hexdigest()

        return json.dumps(
            {
                "op": "auth",
                "args": [self.api_key, expires, signature],
            }
        )

    def subscribe(self, topics: list[str]) -> None:
        """
        Subscribe to market data topics.

        Args:
            topics: List of Bybit topic strings (e.g. ["tickers.BTCUSDT", "orderbook.50.ETHUSDT"])
        """
        with self._lock:
            for t in topics:
                if t not in self._active_args:
                    self._active_args.append(t)

        if self._connected:
            self._send_subscribe(topics)

    def unsubscribe(self, topics: list[str]) -> None:
        """Unsubscribe from topics."""
        with self._lock:
            for t in topics:
                if t in self._active_args:
                    self._active_args.remove(t)

        if self._connected:
            msg = json.dumps({"op": "unsubscribe", "args": topics})
            self._send(msg)

        if not self._active_args:
            logger.info("BybitWS: no topics remaining, disconnecting")
            self.close_connection()

    def connect(self) -> None:
        """Start the WebSocket connection (blocking — run in a thread)."""
        self._stop_flag = False
        retry_attempts = 0
        delay = self.retry_delay

        while not self._stop_flag and retry_attempts <= self.max_retry_attempt:
            try:
                logger.info(f"BybitWS connecting to {self.ws_url} (attempt {retry_attempts + 1})")
                self.wsapp = websocket.WebSocketApp(
                    self.ws_url,
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
                logger.warning(f"BybitWS disconnected; retry in {delay}s")
                time.sleep(delay)
                delay = min(delay * self.retry_multiplier, 60)

            except Exception as exc:
                logger.error(f"BybitWS connect error: {exc}")
                retry_attempts += 1
                time.sleep(delay)
                delay = min(delay * self.retry_multiplier, 60)

        if retry_attempts > self.max_retry_attempt:
            logger.error("BybitWS max reconnect attempts reached; giving up")

    def close_connection(self) -> None:
        """Cleanly stop the WebSocket."""
        self._stop_flag = True
        if self.wsapp:
            try:
                self.wsapp.close()
            except Exception:
                pass

    # ── internal methods ──────────────────────────────────────────────────────

    def _send(self, text: str) -> None:
        if self.wsapp and self._connected:
            try:
                self.wsapp.send(text)
            except Exception as exc:
                logger.error("BybitWS _send error: %s", exc)

    def _send_subscribe(self, topics: list[str]) -> None:
        """Send a subscribe message."""
        msg = json.dumps({"op": "subscribe", "args": topics})
        self._send(msg)

    def _ws_on_open(self, wsapp) -> None:
        logger.info("BybitWS connected")
        with self._lock:
            self._connected = True

        # Send auth for private streams if credentials are available
        if self.api_key and self.api_secret:
            try:
                wsapp.send(self._build_auth_msg())
                logger.info("BybitWS auth sent")
            except Exception as exc:
                logger.error("BybitWS auth error: %s", exc)

        # Re-subscribe to all active topics on reconnect
        with self._lock:
            topics_to_replay = list(self._active_args)

        if topics_to_replay:
            self._send_subscribe(topics_to_replay)
            logger.info(f"BybitWS re-subscribed to {len(topics_to_replay)} topics")

        self.on_open(wsapp)

    def _ws_on_message(self, wsapp, raw) -> None:
        try:
            msg = json.loads(raw)
        except Exception:
            logger.debug(f"BybitWS non-JSON message: {raw[:120]}")
            return

        msg_type = msg.get("type", "")
        op = msg.get("op", "")
        ret_code = msg.get("retCode", 0)
        success = msg.get("success", True)

        # Handle subscription acknowledgments
        if op == "subscribe" and success:
            logger.info(f"BybitWS subscribed: {msg.get('args', [])}")
            return
        if op == "unsubscribe" and success:
            logger.debug(f"BybitWS unsubscribed: {msg.get('args', [])}")
            return
        if op == "auth":
            if success:
                logger.info("BybitWS auth successful")
            else:
                logger.error(f"BybitWS auth failed: {msg}")
            return

        # Handle pong
        if op == "pong":
            return

        # Handle operational messages
        if msg_type in ("snapshot", "delta"):
            self.on_message(wsapp, msg)
        elif "topic" in msg and "data" in msg:
            self.on_message(wsapp, msg)
        else:
            logger.debug(
                f"BybitWS unhandled message: {list(msg.keys()) if isinstance(msg, dict) else type(msg)}"
            )

    def _ws_on_error(self, wsapp, error) -> None:
        logger.error(f"BybitWS error: {error}")
        self.on_error(wsapp, error)

    def _ws_on_close(self, wsapp, *args) -> None:
        logger.info("BybitWS closed")
        with self._lock:
            self._connected = False
        self.on_close(wsapp)
