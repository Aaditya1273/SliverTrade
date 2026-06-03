"""
Zerodha WebSocket streaming module for SilverTrade AI.

This module provides WebSocket integration with Zerodha's market data streaming API,
following the SilverTrade WebSocket proxy architecture.
"""

from .zerodha_adapter import ZerodhaWebSocketAdapter

__all__ = ["ZerodhaWebSocketAdapter"]
