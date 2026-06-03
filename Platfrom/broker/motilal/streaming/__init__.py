"""
Motilal Oswal WebSocket streaming module for SilverTrade AI.

This module provides WebSocket streaming functionality for Motilal Oswal broker,
integrating with SilverTrade's WebSocket proxy infrastructure.
"""

from .motilal_adapter import MotilalWebSocketAdapter
from .motilal_mapping import MotilalCapabilityRegistry, MotilalExchangeMapper

__all__ = ["MotilalWebSocketAdapter", "MotilalExchangeMapper", "MotilalCapabilityRegistry"]
