"""
Binance margin calculation.

For spot trading, Binance does not have a margin calculation API endpoint.
Margin is simply the total value of the assets being traded.

For isolated margin, Binance has dedicated endpoints under /sapi/v1/margin/.

This module is primarily a placeholder for interface compatibility — spot
trading on Binance doesn't require margin in the same way that Indian
brokers or crypto derivatives do.

References:
  https://binance-docs.github.io/apidocs/spot/en/#margin-account-trade
"""

import os

from broker.binance.api.baseurl import get_api_response
from utils.logging import get_logger

logger = get_logger(__name__)


def calculate_margin_api(positions, auth):
    """
    Calculate margin requirement for a basket of positions.

    For Binance Spot, margin is the total position value (no leverage).
    Returns aggregated margin across all positions.

    Args:
        positions: List of SilverTrade-format position dicts
        auth (str): Binance API key stored in auth DB.

    Returns:
        Tuple of (MockResponse, response_data)
    """
    class MockResponse:
        def __init__(self, code):
            self.status_code = code
            self.status = code

    api_key = auth
    api_secret = os.getenv("BROKER_API_SECRET", "")

    if not api_key or not api_secret:
        return MockResponse(401), {
            "status": "error",
            "message": "BROKER_API_KEY / BROKER_API_SECRET not configured",
        }

    if not positions:
        return MockResponse(200), {
            "status": "success",
            "data": {
                "total_margin_required": 0.0,
                "span_margin": 0.0,
                "exposure_margin": 0.0,
            },
        }

    total_margin = 0.0
    for pos in positions:
        try:
            price = float(pos.get("price", 0))
            quantity = float(pos.get("quantity", 0))
            total_margin += price * quantity
        except (ValueError, TypeError):
            continue

    return MockResponse(200), {
        "status": "success",
        "data": {
            "total_margin_required": total_margin,
            "span_margin": total_margin,
            "exposure_margin": 0.0,
        },
    }
