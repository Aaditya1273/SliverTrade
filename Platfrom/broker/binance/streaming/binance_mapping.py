"""
binance_mapping.py

Exchange / mode / capability mappings for Binance WebSocket adapter.

Binance WebSocket streams:
  <symbol>@ticker          – 24hr rolling ticker (LTP, volume, high, low, etc.)
  <symbol>@bookTicker      – Best bid/ask (real-time)
  <symbol>@depth20         – 20-level order book snapshot
  <symbol>@depth@100ms     – 5/10/20 level order book (100ms updates)
  <symbol>@kline_<interval> – Kline/candlestick updates
  
Combined streams:
  /stream?streams=<stream1>/<stream2>/...

References:
  https://binance-docs.github.io/apidocs/spot/en/#websocket-market-streams
"""

import logging


class BinanceExchangeMapper:
    """Maps SilverTrade AI exchange codes to Binance equivalents."""

    EXCHANGE_SEGMENTS = {
        "CRYPTO": "CRYPTO",
    }

    @staticmethod
    def get_segment(exchange: str) -> str:
        return BinanceExchangeMapper.EXCHANGE_SEGMENTS.get(exchange, "CRYPTO")

    @staticmethod
    def get_channel_symbol(br_symbol: str) -> str:
        """Return the symbol string used in Binance WS channel subscriptions."""
        return br_symbol.lower()  # Binance requires lowercase symbols in WS streams


class BinanceModeMapper:
    """Maps SilverTrade AI subscription mode integers to Binance stream names."""

    # SilverTrade AI mode → Binance stream suffix
    MODE_STREAMS = {
        1: "ticker",         # LTP mode → 24hr ticker (includes lastPrice)
        2: "bookTicker",     # Quote mode → best bid/ask
        3: "depth20",        # Depth mode → 20-level order book
    }

    @staticmethod
    def get_stream(mode: int) -> str:
        return BinanceModeMapper.MODE_STREAMS.get(mode, "ticker")

    @staticmethod
    def get_mode_str(mode: int) -> str:
        return {1: "LTP", 2: "QUOTE", 3: "DEPTH"}.get(mode, "LTP")


class BinanceCapabilityRegistry:
    """Registry of Binance broker capabilities."""

    exchanges = ["CRYPTO"]

    # Modes: 1 = LTP, 2 = Quote, 3 = Depth
    subscription_modes = [1, 2, 3]

    depth_support = {
        "CRYPTO": [1, 5, 10, 20],
    }

    @classmethod
    def get_supported_depth_levels(cls, exchange: str) -> list:
        return cls.depth_support.get(exchange, [1])

    @classmethod
    def is_depth_level_supported(cls, exchange: str, depth_level: int) -> bool:
        return depth_level in cls.get_supported_depth_levels(exchange)

    @classmethod
    def get_fallback_depth_level(cls, exchange: str, requested_depth: int) -> int:
        supported = cls.get_supported_depth_levels(exchange)
        if requested_depth in supported:
            return requested_depth
        return max(supported)

    @classmethod
    def supports_mode(cls, mode: int) -> bool:
        return mode in cls.subscription_modes
