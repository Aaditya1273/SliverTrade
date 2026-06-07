"""
SilverTrade Compatibility Package
==================================

Compatibility wrapper that re-exports the ``api`` class from the
``silvertrade_sdk`` package so that legacy test files and user scripts
can continue to write::

    from silvertrade import api

instead of::

    from silvertrade_sdk import api

The ``silvertrade_sdk`` package is the canonical SDK module; this package
exists solely for backward compatibility.
"""

from silvertrade_sdk.api import api

__version__ = "1.0.0"
__all__ = ["api"]
