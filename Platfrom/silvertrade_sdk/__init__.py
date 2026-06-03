"""
SilverTrade AI SDK Module
=========================
Internal replacement for the `openalgo` PyPI package.
Provides the same `api` class interface that the platform expects.

The actual SDK logic is delegated to the platform's internal REST API
endpoints and the existing service layer.
"""

from silvertrade_sdk.api import api

__version__ = "1.0.0"
__all__ = ["api"]
