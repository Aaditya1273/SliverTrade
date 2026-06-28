"""
bybit_mapping.py

Exchange / mode / capability mappings for Bybit WebSocket adapter.

Bybit WebSocket stream names (Public):
  orderbook.200.{symbol}@100ms  – Order book snapshot with 200 levels, 100ms updates
  tickers.{symbol}              – Real-time ticker updates
  kline.{interval}.{symbol}     – Kline/candlestick updates
  publicTrade.{symbol}          – Public trade feed

Combined streams:
  Bybit WebSocket supports subscribing to multiple topics at once.

References:
  https://bybit-exchange.github.io/docs/v5/websocket/public/ticker
"""


class BybitExchangeMapper:
    """Maps SilverTrade AI exchange codes to Bybit equivalents."""

    EXCHANGE_SEGMENTS = {
        "CRYPTO": "CRYPTO",
    }

    @staticmethod
    def get_segment(exchange: str) -> str:
        return BybitExchangeMapper.EXCHANGE_SEGMENTS.get(exchange, "CRYPTO")

    @staticmethod
    def get_channel_symbol(br_symbol: str) -> str:
        """Return the symbol string used in Bybit WS channel subscriptions."""
        return br_symbol  # Bybit uses uppercase symbols in WS topics


class BybitModeMapper:
    """Maps SilverTrade AI subscription mode integers to Bybit stream topics."""

    MODE_TOPICS = {
        1: "tickers",  # LTP → tickers stream
        2: "tickers",  # Quote → tickers stream (includes bid/ask)
        3: "orderbook.50",  # Depth → orderbook.50 (50 levels)
    }

    @staticmethod
    def get_topic(mode: int) -> str:
        return BybitModeMapper.MODE_TOPICS.get(mode, "tickers")

    @staticmethod
    def get_topic_for_symbol(br_symbol: str, mode: int) -> str:
        """Build the full Bybit topic string for a symbol and mode."""
        topic = BybitModeMapper.get_topic(mode)
        return f"{topic}.{br_symbol}"

    @staticmethod
    def get_mode_str(mode: int) -> str:
        return {1: "LTP", 2: "QUOTE", 3: "DEPTH"}.get(mode, "LTP")


class BybitCapabilityRegistry:
    """Registry of Bybit broker capabilities."""

    exchanges = ["CRYPTO"]

    # Modes: 1 = LTP, 2 = Quote, 3 = Depth
    subscription_modes = [1, 2, 3]

    depth_support = {
        "CRYPTO": [1, 50, 200],
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
