"""
Mapping utilities for Dhan broker integration.
Provides exchange code mappings between SilverTrade AI and Dhan formats.
"""

from typing import Dict

# Exchange code mappings
# SilverTrade AI exchange code -> Dhan exchange code
SILVERTRADE_TO_DHAN_EXCHANGE = {
    "NSE": "NSE_EQ",
    "BSE": "BSE_EQ",
    "NFO": "NSE_FNO",
    "BFO": "BSE_FNO",
    "CDS": "NSE_CURRENCY",
    "BCD": "BSE_CURRENCY",
    "MCX": "MCX_COMM",
    "NSE_INDEX": "IDX_I",
    "BSE_INDEX": "IDX_I",
}

# Dhan exchange code -> SilverTrade AI exchange code
DHAN_TO_SILVERTRADE_EXCHANGE = {v: k for k, v in SILVERTRADE_TO_DHAN_EXCHANGE.items()}


def get_dhan_exchange(silvertrade_exchange: str) -> str:
    """
    Convert SilverTrade AI exchange code to Dhan exchange code.

    Args:
        silvertrade_exchange (str): Exchange code in SilverTrade AI format

    Returns:
        str: Exchange code in Dhan format
    """
    return SILVERTRADE_TO_DHAN_EXCHANGE.get(silvertrade_exchange, silvertrade_exchange)


def get_silvertrade_exchange(dhan_exchange: str) -> str:
    """
    Convert Dhan exchange code to SilverTrade AI exchange code.

    Args:
        dhan_exchange (str): Exchange code in Dhan format

    Returns:
        str: Exchange code in SilverTrade AI format
    """
    return DHAN_TO_SILVERTRADE_EXCHANGE.get(dhan_exchange, dhan_exchange)
