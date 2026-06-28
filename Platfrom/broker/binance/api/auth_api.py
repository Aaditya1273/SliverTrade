"""
Binance Authentication Module.

Binance uses API Key + Secret Key authentication (no OAuth flow).
Credentials are provided once via environment variables BROKER_API_KEY and
BROKER_API_SECRET. This function validates that both vars are present and
then calls GET /api/v3/account to confirm the key is valid and active.

Returns:
    (api_key, None)          on success
    (None, error_message)    on failure
"""

import os

from broker.binance.api.baseurl import get_api_response
from utils.logging import get_logger

logger = get_logger(__name__)


def authenticate_broker(code=None):
    """
    Authenticate with Binance using API Key + Secret Key.

    Binance does NOT use an OAuth flow — credentials are provided once
    via environment variables. This function validates that both vars are
    present and then makes a signed GET /api/v3/account call to confirm
    the key is valid and active.

    Args:
        code: Not used for Binance (kept for interface compatibility).

    Returns:
        (api_key, None)          on success
        (None, error_message)    on failure
    """
    try:
        api_key = os.getenv("BROKER_API_KEY", "").strip()
        api_secret = os.getenv("BROKER_API_SECRET", "").strip()

        if not api_key:
            return None, "BROKER_API_KEY is not set in environment variables"
        if not api_secret:
            return None, "BROKER_API_SECRET is not set in environment variables"

        # Verify credentials with a live signed request to GET /api/v3/account
        logger.info("Verifying Binance credentials via GET /api/v3/account")
        result = get_api_response(
            endpoint="/api/v3/account",
            api_key=api_key,
            api_secret=api_secret,
            method="GET",
            signed=True,
            trade_type="SPOT",
        )

        if result.get("success"):
            data = result.get("result", {})
            # Binance returns account info with 'balances', 'canTrade', 'canWithdraw', etc.
            can_trade = data.get("canTrade", False)
            if can_trade:
                logger.info("Binance authentication successful — account is enabled for trading")
                return api_key, None
            else:
                msg = (
                    "Binance account exists but trading is not enabled. "
                    "Check your account permissions in the Binance dashboard."
                )
                logger.error(msg)
                return None, msg

        error = result.get("error", {})
        err_code = error.get("code", "unknown")
        err_msg = error.get("message", "Unknown error")

        if err_code == -2015:
            msg = (
                "Invalid API key, secret, or signature format. "
                "Verify BROKER_API_KEY and BROKER_API_SECRET in your .env file. "
                "Ensure the API key has trading permissions enabled."
            )
        elif err_code == -2014:
            msg = "API key format is invalid. Check that BROKER_API_KEY is a valid Binance API key."
        else:
            msg = f"Binance API error (code={err_code}): {err_msg}"

        logger.error(msg)
        return None, msg

    except Exception as e:
        msg = f"An exception occurred during Binance authentication: {str(e)}"
        logger.exception(msg)
        return None, msg
