"""
Bybit margin calculation.

For spot trading, Bybit does not have a dedicated margin calculation API endpoint.
Margin is the total value of the assets being traded.

For derivatives (linear futures), the endpoint /v5/position/list can be used.

This module is primarily a placeholder for interface compatibility.
"""

import os

from broker.bybit.api.baseurl import get_api_response
from utils.logging import get_logger

logger = get_logger(__name__)


def calculate_margin_api(positions, auth):
    """
    Calculate margin requirement for a basket of positions.

    For Bybit Spot, margin is the total position value.
    Returns aggregated margin across all positions.

    Args:
        positions: List of SilverTrade-format position dicts
        auth (str): Bybit API key stored in auth DB.

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
