"""
Binance Wallet Balance → SilverTrade AI margin format.

Endpoints:
  GET /api/v3/account    → Account balances (free + locked)
  GET /sapi/v1/asset/tradeFee → Trading fee rates (optional)

Binance Spot account balances:
    balances: [{"asset": "BTC", "free": "0.001", "locked": "0.000"}, ...]

SilverTrade margin field mapping:
    availablecash   ← sum of (free * USDT_price) for all non-zero assets
    collateral      ← sum of locked balances
    utiliseddebits  ← sum of locked balances
    m2mrealized     ← 0 (Binance doesn't expose P&L in account endpoint)
    m2munrealized   ← 0

References:
  https://binance-docs.github.io/apidocs/spot/en/#account-information-user_data
"""

import os

from broker.binance.api.baseurl import get_api_response
from utils.logging import get_logger

logger = get_logger(__name__)

DEFAULT_MARGIN_RESPONSE = {
    "availablecash": "0.00",
    "collateral": "0.00",
    "m2mrealized": "0.00",
    "m2munrealized": "0.00",
    "utiliseddebits": "0.00",
}


def _f(value):
    """Safe float conversion from string or number."""
    try:
        return float(value or 0)
    except (ValueError, TypeError):
        return 0.0


def get_margin_data(auth_token):
    """
    Fetch account balance from Binance and return it in SilverTrade AI margin format.

    Binance account fields used:
        balances[].asset   – asset symbol (e.g. "BTC", "USDT")
        balances[].free    – available balance
        balances[].locked  – locked in orders

    For simplicity, we report the total USDT-equivalent value using prices
    from /api/v3/ticker/price.

    Args:
        auth_token (str): Binance API key stored in auth DB.

    Returns:
        dict: SilverTrade AI standard margin dict, or DEFAULT_MARGIN_RESPONSE on failure.
    """
    api_key = auth_token
    api_secret = os.getenv("BROKER_API_SECRET", "")

    if not api_key or not api_secret:
        logger.error("[Binance] BROKER_API_KEY / BROKER_API_SECRET not set")
        return DEFAULT_MARGIN_RESPONSE

    try:
        # Fetch account info
        result = get_api_response("/api/v3/account", api_key, api_secret, method="GET", signed=True)
        if not result.get("success"):
            error = result.get("error", {})
            logger.error(f"[Binance] Account API error: {error}")
            return DEFAULT_MARGIN_RESPONSE

        data = result.get("result", {})
        balances = data.get("balances", [])

        # Get USDT prices for all assets (for USD-equivalent calculation)
        prices = {}
        try:
            price_result = get_api_response("/api/v3/ticker/price")
            if price_result.get("success"):
                for price_entry in price_result.get("result", []):
                    if isinstance(price_entry, dict):
                        prices[price_entry.get("symbol", "")] = _f(price_entry.get("price", 0))
        except Exception as e:
            logger.warning(f"[Binance] Could not fetch prices: {e}")

        # Calculate totals in USDT
        total_free_usdt = 0.0
        total_locked_usdt = 0.0

        for balance in balances:
            asset = balance.get("asset", "")
            free = _f(balance.get("free", 0))
            locked = _f(balance.get("locked", 0))

            if free == 0 and locked == 0:
                continue

            # Get price in USDT
            if asset == "USDT":
                price_usdt = 1.0
            elif asset == "USDC":
                price_usdt = 1.0  # Approximate
            elif asset == "BUSD":
                price_usdt = 1.0
            elif asset == "FDUSD":
                price_usdt = 1.0
            else:
                # Look up the price for the trading pair
                pair = f"{asset}USDT"
                price_usdt = prices.get(pair, 0)
                if price_usdt == 0:
                    # Try alternative pairs
                    pair = f"{asset}BUSD"
                    price_usdt = prices.get(pair, 0)

            total_free_usdt += free * price_usdt
            total_locked_usdt += locked * price_usdt

        result_data = {
            "availablecash": f"{total_free_usdt:.2f}",
            "collateral": f"{total_locked_usdt:.2f}",
            "m2mrealized": "0.00",
            "m2munrealized": "0.00",
            "utiliseddebits": f"{total_locked_usdt:.2f}",
        }

        logger.debug(
            f"[Binance] Wallet: available={result_data['availablecash']} "
            f"locked={result_data['utiliseddebits']}"
        )
        return result_data

    except Exception as e:
        logger.error(f"[Binance] Error in get_margin_data: {e}", exc_info=True)
        return DEFAULT_MARGIN_RESPONSE
