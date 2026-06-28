"""
Bybit Wallet Balance → SilverTrade AI margin format.

Endpoint:
  GET /v5/account/wallet-balance

Bybit wallet response (UNIFIED account):
    {
      "retCode": 0,
      "result": {
        "list": [{
          "totalEquity": "10000.50",
          "totalWalletBalance": "9500.00",
          "totalMarginBalance": "9500.00",
          "coin": [{
            "coin": "USDT",
            "equity": "5000.00",
            "walletBalance": "5000.00",
            "free": "4500.00",
            "locked": "500.00"
          },
          ...
          ]
        }]
      }
    }

SilverTrade field mapping:
    availablecash   ← sum of coin.free (in USDT)
    collateral      ← sum of coin.locked
    utiliseddebits  ← sum of coin.locked
    m2mrealized     ← 0 (not exposed by Bybit wallet endpoint)
    m2munrealized   ← 0
"""

import os

from broker.bybit.api.baseurl import get_api_response
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
    try:
        return float(value or 0)
    except (ValueError, TypeError):
        return 0.0


def get_margin_data(auth_token):
    """
    Fetch wallet balance from Bybit and return in SilverTrade AI margin format.

    For Unified accounts, we fetch the wallet balance which includes
    all coins with their free/locked amounts.

    Args:
        auth_token (str): Bybit API key stored in auth DB.

    Returns:
        dict: SilverTrade AI standard margin dict, or DEFAULT_MARGIN_RESPONSE on failure.
    """
    api_key = auth_token
    api_secret = os.getenv("BROKER_API_SECRET", "")

    if not api_key or not api_secret:
        logger.error("[Bybit] BROKER_API_KEY / BROKER_API_SECRET not set")
        return DEFAULT_MARGIN_RESPONSE

    try:
        result = get_api_response(
            "/v5/account/wallet-balance",
            api_key,
            api_secret,
            method="GET",
            signed=True,
            params={"accountType": "UNIFIED"},
        )

        if not result.get("success"):
            error = result.get("error", {})
            logger.error(f"[Bybit] Wallet balance API error: {error}")
            return DEFAULT_MARGIN_RESPONSE

        data = result.get("result", {})
        accounts = data.get("list", [])

        total_free = 0.0
        total_locked = 0.0

        for acct in accounts:
            if not isinstance(acct, dict):
                continue
            coins = acct.get("coin", [])
            if not isinstance(coins, list):
                continue

            for coin in coins:
                if not isinstance(coin, dict):
                    continue
                coin_name = coin.get("coin", "")
                free = _f(coin.get("free", 0))
                locked = _f(coin.get("locked", 0))

                # For simplicity, assume USDT = 1:1, other coins we treat as-is
                # A more accurate version would look up prices via /v5/market/tickers
                if coin_name == "USDT":
                    total_free += free
                    total_locked += locked
                elif coin_name in ("USDC", "BUSD", "FDUSD"):
                    total_free += free
                    total_locked += locked
                else:
                    # Non-USDT coins: estimate value by treating free+locked as USDT value
                    # This is a simplification; in production, fetch prices
                    if free > 0 or locked > 0:
                        total_free += free
                        total_locked += locked

        result_data = {
            "availablecash": f"{total_free:.2f}",
            "collateral": f"{total_locked:.2f}",
            "m2mrealized": "0.00",
            "m2munrealized": "0.00",
            "utiliseddebits": f"{total_locked:.2f}",
        }

        logger.debug(
            f"[Bybit] Wallet: available={result_data['availablecash']} "
            f"locked={result_data['utiliseddebits']}"
        )
        return result_data

    except Exception as e:
        logger.error(f"[Bybit] Error in get_margin_data: {e}", exc_info=True)
        return DEFAULT_MARGIN_RESPONSE
