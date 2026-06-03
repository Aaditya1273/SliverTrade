"""
Kotak WebSocket streaming integration for SilverTrade AI.
Exposes the high-level adapter and core websocket client.
"""

from .kotak_adapter import KotakWebSocketAdapter
from .kotak_websocket import KotakWebSocket

__all__ = ["KotakWebSocketAdapter", "KotakWebSocket"]
