"""
Nubra WebSocket streaming module for SilverTrade AI.

This module provides WebSocket integration with Nubra's market data streaming API,
following the SilverTrade WebSocket proxy architecture.
"""

from .nubra_adapter import NubraWebSocketAdapter

__all__ = ["NubraWebSocketAdapter"]
