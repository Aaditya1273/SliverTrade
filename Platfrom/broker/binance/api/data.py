"""
Binance Market Data Provider.

Public endpoints (no auth required):
  GET /api/v3/ticker/24hr   → 24hr ticker (LTP, volume, high, low, etc.)
  GET /api/v3/ticker/bookTicker → Best bid/ask
  GET /api/v3/depth          → Order book depth
  GET /api/v3/klines         → OHLCV candlestick data
  GET /api/v3/exchangeInfo   → Trading rules & symbol info

References:
  https://binance-docs.github.io/apidocs/spot/en/#market-data-endpoints
"""

import os
import time
from datetime import datetime, timedelta

import pandas as pd

from broker.binance.api.baseurl import get_api_response
from database.token_db import get_br_symbol, get_token
from utils.logging import get_logger

logger = get_logger(__name__)


def _f(value, default=0.0):
    """Safe float cast."""
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def _i(value, default=0):
    """Safe int cast."""
    try:
        return int(float(value)) if value is not None else default
    except (ValueError, TypeError):
        return default


class BrokerData:
    """
    Binance market data provider.

    Public endpoints are called without authentication.
    """

    # Binance candle interval codes mapped from SilverTrade AI interval codes.
    TIMEFRAME_MAP = {
        "1m":  "1m",
        "3m":  "3m",
        "5m":  "5m",
        "15m": "15m",
        "30m": "30m",
        "1h":  "1h",
        "2h":  "2h",
        "4h":  "4h",
        "6h":  "6h",
        "8h":  "8h",
        "12h": "12h",
        "1d":  "1d",
        "D":   "1d",
        "3d":  "3d",
        "1w":  "1w",
        "W":   "1w",
        "1M":  "1M",
    }

    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.timeframe_map = self.TIMEFRAME_MAP

    # ─────────────────────────────────────────────────────────────────────────────
    # get_quotes
    # ─────────────────────────────────────────────────────────────────────────────

    def get_quotes(self, symbol: str, exchange: str) -> dict:
        """
        Fetch real-time quote for a single symbol.

        Calls: GET /api/v3/ticker/24hr

        Field mapping:
            ltp        ← lastPrice
            open       ← openPrice
            high       ← highPrice
            low        ← lowPrice
            volume     ← volume
            prev_close ← prevClosePrice
            bid        ← bidPrice
            ask        ← askPrice
            oi         ← 0 (Binance doesn't provide OI for spot)

        Returns:
            dict with ltp, open, high, low, volume, prev_close, oi, bid, ask
        """
        try:
            br_symbol = self._get_br_symbol(symbol, exchange)
            logger.info(f"[Binance] get_quotes: {symbol} → {br_symbol}")

            result = get_api_response(
                "/api/v3/ticker/24hr",
                params={"symbol": br_symbol}
            )

            if not result.get("success"):
                raise Exception(f"Ticker API error: {result.get('error', {})}")

            ticker = result.get("result", {})

            return {
                "ltp":        _f(ticker.get("lastPrice", 0)),
                "open":       _f(ticker.get("openPrice", 0)),
                "high":       _f(ticker.get("highPrice", 0)),
                "low":        _f(ticker.get("lowPrice", 0)),
                "volume":     _f(ticker.get("volume", 0)),
                "prev_close": _f(ticker.get("prevClosePrice", 0)),
                "oi":         0.0,  # Binance Spot doesn't have OI
                "bid":        _f(ticker.get("bidPrice", 0)),
                "ask":        _f(ticker.get("askPrice", 0)),
            }

        except Exception as e:
            logger.error(f"[Binance] get_quotes error for {symbol}: {e}")
            raise Exception(f"Error fetching quotes for {symbol}: {e}")

    # ─────────────────────────────────────────────────────────────────────────────
    # get_depth
    # ─────────────────────────────────────────────────────────────────────────────

    def get_depth(self, symbol: str, exchange: str) -> dict:
        """
        Fetch market depth for a symbol.

        Calls: GET /api/v3/depth?symbol=BTCUSDT&limit=20

        Binance depth response:
            { "lastUpdateId": ..., "bids": [["price", "qty"], ...], "asks": [...] }

        Returns dict with:
            bids, asks – list of 5 × {"price": float, "quantity": float}
            ltp, volume, open, high, low, prev_close, oi
            totalbuyqty, totalsellqty
        """
        try:
            br_symbol = self._get_br_symbol(symbol, exchange)
            logger.info(f"[Binance] get_depth: {symbol} → {br_symbol}")

            # Also fetch ticker for LTP / OHLCV
            ticker_result = get_api_response(
                "/api/v3/ticker/24hr", params={"symbol": br_symbol}
            )
            ticker = ticker_result.get("result", {}) if ticker_result.get("success") else {}

            ltp = _f(ticker.get("lastPrice", 0))

            # Fetch depth
            depth_result = get_api_response(
                "/api/v3/depth", params={"symbol": br_symbol, "limit": 20}
            )

            bids_raw = []
            asks_raw = []
            if depth_result.get("success"):
                depth_data = depth_result.get("result", {})
                bids_raw = depth_data.get("bids", [])
                asks_raw = depth_data.get("asks", [])

            def _parse_levels(levels, n=5):
                out = []
                for lvl in levels[:n]:
                    if len(lvl) >= 2:
                        out.append({
                            "price":    _f(lvl[0]),
                            "quantity": _f(lvl[1]),
                        })
                while len(out) < n:
                    out.append({"price": 0.0, "quantity": 0})
                return out

            bids = _parse_levels(bids_raw)
            asks = _parse_levels(asks_raw)

            return {
                "bids": bids,
                "asks": asks,
                "ltp":          ltp,
                "ltq":          0,
                "volume":       _f(ticker.get("volume", 0)),
                "open":         _f(ticker.get("openPrice", 0)),
                "high":         _f(ticker.get("highPrice", 0)),
                "low":          _f(ticker.get("lowPrice", 0)),
                "prev_close":   _f(ticker.get("prevClosePrice", 0)),
                "oi":           0.0,
                "totalbuyqty":  sum(lvl["quantity"] for lvl in bids),
                "totalsellqty": sum(lvl["quantity"] for lvl in asks),
            }

        except Exception as e:
            logger.error(f"[Binance] get_depth error for {symbol}: {e}")
            raise Exception(f"Error fetching depth for {symbol}: {e}")

    # ─────────────────────────────────────────────────────────────────────────────
    # get_history
    # ─────────────────────────────────────────────────────────────────────────────

    def get_history(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV klines from Binance.

        Endpoint: GET /api/v3/klines
        Params:
            symbol    – trading pair (e.g. "BTCUSDT")
            interval  – candle interval code (e.g. "1h", "1d")
            startTime – Unix epoch milliseconds
            endTime   – Unix epoch milliseconds
            limit     – max 1000 candles per request

        Response format (array-of-arrays):
            [
              [1499040000000, "0.01634790", "0.80000000", "0.01575800",
               "0.01577100", "148976.11427815", 1499644799999,
               "2434.19055334", 308, "1756.87426997", "0"],
              ...
            ]
            Index: 0=open_time, 1=open, 2=high, 3=low, 4=close, 5=volume

        Returns:
            pd.DataFrame with [timestamp, open, high, low, close, volume, oi]
        """
        try:
            if interval not in self.TIMEFRAME_MAP:
                supported = list(self.TIMEFRAME_MAP.keys())
                raise Exception(f"Unsupported interval '{interval}'. Supported: {', '.join(supported)}")

            resolution = self.TIMEFRAME_MAP[interval]
            br_symbol = self._get_br_symbol(symbol, exchange)

            # Parse dates
            from datetime import date as _date, time as _time
            if isinstance(start_date, str):
                start_dt = datetime.strptime(start_date, "%Y-%m-%d")
            else:
                start_dt = datetime.combine(start_date, _time.min)

            if isinstance(end_date, str):
                end_dt = datetime.strptime(end_date, "%Y-%m-%d")
            else:
                end_dt = datetime.combine(end_date, _time.min)

            start_ms = int(start_dt.timestamp() * 1000)
            end_ms = int(end_dt.timestamp() * 1000)

            # Binance limit is 1000 per request; chunk if needed
            # Calculate chunk size in ms
            resolution_ms = {
                "1m": 60000, "3m": 180000, "5m": 300000, "15m": 900000,
                "30m": 1800000, "1h": 3600000, "2h": 7200000, "4h": 14400000,
                "6h": 21600000, "8h": 28800000, "12h": 43200000,
                "1d": 86400000, "3d": 259200000, "1w": 604800000, "1M": 2592000000,
            }
            chunk_ms = resolution_ms.get(resolution, 86400000) * 1000  # 1000 candles per chunk
            if chunk_ms <= 0:
                chunk_ms = 86400000 * 1000  # fallback

            chunks = []
            cursor = start_ms
            while cursor < end_ms:
                chunk_end = min(cursor + chunk_ms - 1, end_ms)
                chunks.append((cursor, chunk_end))
                cursor = chunk_end + 1

            logger.info(f"[Binance] get_history: {br_symbol} {resolution} "
                       f"({len(chunks)} chunk(s))")

            all_candles = []

            for chunk_start, chunk_end in chunks:
                params = {
                    "symbol": br_symbol,
                    "interval": resolution,
                    "startTime": chunk_start,
                    "endTime": chunk_end,
                    "limit": 1000,
                }

                kline_result = get_api_response("/api/v3/klines", params=params)
                if not kline_result.get("success"):
                    raise Exception(f"Klines API error: {kline_result.get('error', {})}")

                raw_klines = kline_result.get("result", [])
                for kline in raw_klines:
                    if isinstance(kline, list) and len(kline) >= 6:
                        all_candles.append({
                            "timestamp": int(kline[0]) // 1000,  # ms → seconds
                            "open":      _f(kline[1]),
                            "high":      _f(kline[2]),
                            "low":       _f(kline[3]),
                            "close":     _f(kline[4]),
                            "volume":    _f(kline[5]),
                            "oi":        0,
                        })

            if all_candles:
                df = pd.DataFrame(all_candles)
                df = df.sort_values("timestamp").drop_duplicates(subset=["timestamp"]).reset_index(drop=True)
                logger.info(f"[Binance] History: {len(df)} candles for {br_symbol} @ {resolution}")
            else:
                df = pd.DataFrame(columns=["timestamp", "open", "high", "low", "close", "volume", "oi"])
                logger.warning(f"[Binance] No candles for {br_symbol} @ {resolution}")

            return df

        except Exception as e:
            logger.error(f"[Binance] get_history error for {symbol}: {e}")
            raise Exception(f"Error fetching history for {symbol}: {e}")

    # ─────────────────────────────────────────────────────────────────────────────
    # get_intervals
    # ─────────────────────────────────────────────────────────────────────────────

    def get_intervals(self) -> list:
        """Return supported intervals, filtering out duplicate aliases (e.g. 'D' → '1d', 'W' → '1w')."""
        # Canonical intervals only: exclude known single-character aliases
        aliases = {"D", "W"}
        canonical = [k for k in self.TIMEFRAME_MAP if k not in aliases]
        return canonical

    # ─────────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ─────────────────────────────────────────────────────────────────────────────

    def _get_br_symbol(self, symbol: str, exchange: str) -> str:
        """Resolve SilverTrade AI symbol → Binance symbol."""
        from database.token_db import get_br_symbol
        br = get_br_symbol(symbol, exchange)
        if not br:
            logger.warning(f"[Binance] brsymbol not found for {symbol}/{exchange}, using symbol as-is")
            return symbol
        return br
