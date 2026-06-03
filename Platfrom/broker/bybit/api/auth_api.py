"""
Bybit Authentication Module.

Bybit uses API Key + Secret Key authentication (no OAuth flow).
Credentials are provided via environment variables BROKER_API_KEY and
BROKER_API_SECRET. This function validates both are present and calls
GET /v5/account/wallet-balance to confirm the key is valid and active.

Returns:
    (api_key, None)          on success
    (None, error_message)    on failure
"""

import os

from broker.bybit.api.baseurl import get_api_response
from utils.logging import get_logger

logger = get_logger(__name__)


def authenticate_broker(code=None):
    """
    Authenticate with Bybit using API Key + Secret Key.

    Validates credentials by making a signed GET /v5/account/wallet-balance
    call to confirm the key is valid and has trading permissions.

    Args:
        code: Not used for Bybit (kept for interface compatibility).

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

        # Verify credentials with a signed request to GET /v5/account/wallet-balance
        logger.info("Verifying Bybit credentials via GET /v5/account/wallet-balance")
        result = get_api_response(
            endpoint="/v5/account/wallet-balance",
            params={"accountType": "UNIFIED"},
            method="GET",
            signed=True,
            category="spot",
        )

        if result.get("success"):
            data = result.get("result", {})
            # Bybit returns account info with account type
            account_type = data.get("accountType", "")
            if account_type:
                logger.info(f"Bybit authentication successful — account type: {account_type}")
                return api_key, None
            else:
                logger.warning("Bybit auth succeeded but no accountType returned — treating as success")
                return api_key, None

        error = result.get("error", {})
        err_code = error.get("code", "unknown")
        err_msg = error.get("message", "Unknown error")

        if err_code == 10003:
            msg = ("Invalid API key or signature. "
                   "Verify BROKER_API_KEY and BROKER_API_SECRET in your .env file.")
        elif err_code == 10004:
            msg = ("API key does not have required permissions. "
                   "Enable trading permissions in the Bybit dashboard.")
        elif err_code == 10002:
            msg = ("Request timestamp is outside the recv_window. "
                   "Check that your system clock is synchronized (NTP).")
        else:
            msg = f"Bybit API error (code={err_code}): {err_msg}"

        logger.error(msg)
        return None, msg

    except Exception as e:
        msg = f"An exception occurred during Bybit authentication: {str(e)}"
        logger.exception(msg)
        return None, msg
