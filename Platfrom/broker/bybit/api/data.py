"""
Bybit Market Data Provider.

Public endpoints (no auth required):
  GET /v5/market/tickers        → Ticker price (24hr)
  GET /v5/market/orderbook      → Order book depth
  GET /v5/market/klines         → OHLCV candlestick data
  GET /v5/market/instruments-info → Trading rules & symbol info

References:
  https://bybit-exchange.github.io/docs/v5/market/tickers
"""

import os
import time
from datetime import datetime, timedelta

import pandas as pd

from broker.bybit.api.baseurl import get_api_response
from utils.logging import get_logger

logger = get_logger(__name__)


def _f(value, default=0.0):
    try:
        return float(value) if value is not None else default
    except (ValueError, TypeError):
        return default


def _i(value, default=0):
    try:
        return int(float(value)) if value is not None else default
    except (ValueError, TypeError):
        return default


class BrokerData:
    """
    Bybit market data provider.

    Public endpoints are called without authentication.
    """

    TIMEFRAME_MAP = {
        "1m": "1",
        "3m": "3",
        "5m": "5",
        "15m": "15",
        "30m": "30",
        "1h": "60",
        "2h": "120",
        "4h": "240",
        "6h": "360",
        "1d": "D",
        "D": "D",
        "1w": "W",
        "W": "W",
        "1M": "M",
    }

    def __init__(self, auth_token: str):
        self.auth_token = auth_token
        self.timeframe_map = self.TIMEFRAME_MAP

    # ──────────────────────────────────────────────────────────────────────────
    # get_quotes
    # ──────────────────────────────────────────────────────────────────────────

    def get_quotes(self, symbol: str, exchange: str) -> dict:
        """
        Fetch real-time quote for a single symbol.

        Calls: GET /v5/market/tickers?category=spot&symbol=BTCUSDT

        Bybit ticker fields:
            lastPrice     → ltp
            open24h       → open
            high24h       → high
            low24h        → low
            volume24h     → volume
            bid1Price     → bid
            ask1Price     → ask
            prevPrice24h  → prev_close
        """
        try:
            br_symbol = self._get_br_symbol(symbol, exchange)
            logger.info(f"[Bybit] get_quotes: {symbol} → {br_symbol}")

            result = get_api_response(
                "/v5/market/tickers", params={"symbol": br_symbol, "category": "spot"}
            )

            if not result.get("success"):
                raise Exception(f"Ticker API error: {result.get('error', {})}")

            data = result.get("result", {})
            ticker_list = data.get("list", [])
            ticker = ticker_list[0] if isinstance(ticker_list, list) and ticker_list else {}

            return {
                "ltp": _f(ticker.get("lastPrice", 0)),
                "open": _f(ticker.get("open24h", 0)),
                "high": _f(ticker.get("high24h", 0)),
                "low": _f(ticker.get("low24h", 0)),
                "volume": _f(ticker.get("volume24h", 0)),
                "prev_close": _f(ticker.get("prevPrice24h", 0)),
                "oi": _f(ticker.get("openInterest", 0)),
                "bid": _f(ticker.get("bid1Price", 0)),
                "ask": _f(ticker.get("ask1Price", 0)),
            }

        except Exception as e:
            logger.error(f"[Bybit] get_quotes error for {symbol}: {e}")
            raise Exception(f"Error fetching quotes for {symbol}: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # get_depth
    # ──────────────────────────────────────────────────────────────────────────

    def get_depth(self, symbol: str, exchange: str) -> dict:
        """
        Fetch market depth for a symbol.

        Calls: GET /v5/market/orderbook?category=spot&symbol=BTCUSDT&limit=50

        Bybit depth response:
            {
              "b": [["price", "size"], ...],  → bids
              "a": [["price", "size"], ...],  → asks
            }
        """
        try:
            br_symbol = self._get_br_symbol(symbol, exchange)
            logger.info(f"[Bybit] get_depth: {symbol} → {br_symbol}")

            # Fetch ticker for LTP
            ticker_result = get_api_response(
                "/v5/market/tickers", params={"symbol": br_symbol, "category": "spot"}
            )
            ltp = 0.0
            if ticker_result.get("success"):
                tlist = ticker_result.get("result", {}).get("list", [])
                if tlist:
                    ltp = _f(tlist[0].get("lastPrice", 0))

            # Fetch depth
            depth_result = get_api_response(
                "/v5/market/orderbook",
                params={"symbol": br_symbol, "category": "spot", "limit": 50},
            )

            bids_raw = []
            asks_raw = []
            if depth_result.get("success"):
                depth_data = depth_result.get("result", {})
                bids_raw = depth_data.get("b", [])
                asks_raw = depth_data.get("a", [])

            def _parse_levels(levels, n=5):
                out = []
                for lvl in levels[:n]:
                    if isinstance(lvl, list) and len(lvl) >= 2:
                        out.append({"price": _f(lvl[0]), "quantity": _f(lvl[1])})
                while len(out) < n:
                    out.append({"price": 0.0, "quantity": 0})
                return out

            bids = _parse_levels(bids_raw)
            asks = _parse_levels(asks_raw)

            # Also fetch ticker for 24hr stats
            volume = 0
            open_p = 0
            high_p = 0
            low_p = 0
            if ticker_result.get("success") and tlist:
                volume = _f(tlist[0].get("volume24h", 0))
                open_p = _f(tlist[0].get("open24h", 0))
                high_p = _f(tlist[0].get("high24h", 0))
                low_p = _f(tlist[0].get("low24h", 0))

            return {
                "bids": bids,
                "asks": asks,
                "ltp": ltp,
                "ltq": 0,
                "volume": volume,
                "open": open_p,
                "high": high_p,
                "low": low_p,
                "prev_close": 0.0,
                "oi": 0.0,
                "totalbuyqty": sum(lvl["quantity"] for lvl in bids),
                "totalsellqty": sum(lvl["quantity"] for lvl in asks),
            }

        except Exception as e:
            logger.error(f"[Bybit] get_depth error for {symbol}: {e}")
            raise Exception(f"Error fetching depth for {symbol}: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # get_history
    # ──────────────────────────────────────────────────────────────────────────

    def get_history(
        self,
        symbol: str,
        exchange: str,
        interval: str,
        start_date: str,
        end_date: str,
    ) -> pd.DataFrame:
        """
        Fetch OHLCV klines from Bybit.

        Endpoint: GET /v5/market/klines
        Params:
            symbol    – trading pair (e.g. "BTCUSDT")
            interval  – kline interval code (e.g. "1", "60", "D", "W")
            start     – Unix epoch milliseconds
            end       – Unix epoch milliseconds
            limit     – max 1000 candles per request

        Response format:
            { "retCode": 0, "result": { "list": [
                ["1670601600000", "16950.0", "17000.0", "16900.0", "16980.0", "123.45", "2100000.99"],
                ...
            ] } }
            Index: 0=startTime, 1=open, 2=high, 3=low, 4=close, 5=volume, 6=turnover
        """
        try:
            if interval not in self.TIMEFRAME_MAP:
                supported = list(self.TIMEFRAME_MAP.keys())
                raise Exception(
                    f"Unsupported interval '{interval}'. Supported: {', '.join(supported)}"
                )

            resolution = self.TIMEFRAME_MAP[interval]
            br_symbol = self._get_br_symbol(symbol, exchange)

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

            # Chunk size: 1000 candles per request
            resolution_ms = {
                "1": 60000,
                "3": 180000,
                "5": 300000,
                "15": 900000,
                "30": 1800000,
                "60": 3600000,
                "120": 7200000,
                "240": 14400000,
                "360": 21600000,
                "D": 86400000,
                "W": 604800000,
                "M": 2592000000,
            }
            chunk_ms = resolution_ms.get(resolution, 86400000) * 1000

            chunks = []
            cursor = start_ms
            while cursor < end_ms:
                chunk_end = min(cursor + chunk_ms - 1, end_ms)
                chunks.append((cursor, chunk_end))
                cursor = chunk_end + 1

            logger.info(f"[Bybit] get_history: {br_symbol} {resolution} ({len(chunks)} chunk(s))")
            all_candles = []

            for chunk_start, chunk_end in chunks:
                params = {
                    "symbol": br_symbol,
                    "interval": resolution,
                    "start": chunk_start,
                    "end": chunk_end,
                    "limit": 1000,
                    "category": "spot",
                }

                kline_result = get_api_response("/v5/market/klines", params=params)
                if not kline_result.get("success"):
                    raise Exception(f"Klines API error: {kline_result.get('error', {})}")

                kline_data = kline_result.get("result", {})
                raw_list = kline_data.get("list", [])

                if isinstance(raw_list, list):
                    for kline in raw_list:
                        if isinstance(kline, list) and len(kline) >= 6:
                            all_candles.append(
                                {
                                    "timestamp": int(kline[0]) // 1000,
                                    "open": _f(kline[1]),
                                    "high": _f(kline[2]),
                                    "low": _f(kline[3]),
                                    "close": _f(kline[4]),
                                    "volume": _f(kline[5]),
                                    "oi": 0,
                                }
                            )

            if all_candles:
                df = pd.DataFrame(all_candles)
                df = (
                    df.sort_values("timestamp")
                    .drop_duplicates(subset=["timestamp"])
                    .reset_index(drop=True)
                )
                logger.info(f"[Bybit] History: {len(df)} candles for {br_symbol} @ {resolution}")
            else:
                df = pd.DataFrame(
                    columns=["timestamp", "open", "high", "low", "close", "volume", "oi"]
                )
                logger.warning(f"[Bybit] No candles for {br_symbol} @ {resolution}")

            return df

        except Exception as e:
            logger.error(f"[Bybit] get_history error for {symbol}: {e}")
            raise Exception(f"Error fetching history for {symbol}: {e}")

    # ──────────────────────────────────────────────────────────────────────────
    # get_intervals
    # ──────────────────────────────────────────────────────────────────────────

    def get_intervals(self) -> list:
        return list(self.TIMEFRAME_MAP.keys())

    # ──────────────────────────────────────────────────────────────────────────
    # Internal helpers
    # ──────────────────────────────────────────────────────────────────────────

    def _get_br_symbol(self, symbol: str, exchange: str) -> str:
        """Resolve SilverTrade symbol → Bybit symbol."""
        from database.token_db import get_br_symbol

        br = get_br_symbol(symbol, exchange)
        if not br:
            logger.warning(
                f"[Bybit] brsymbol not found for {symbol}/{exchange}, using symbol as-is"
            )
            return symbol
        return br
