"""
Binance API Base URL Configuration and HMAC-SHA256 Signing.

Authentication:
  Binance uses HMAC-SHA256 signed requests for private endpoints.
  All signed requests require:
    - X-MBX-APIKEY header set to the API key
    - A 'signature' query parameter: HMAC-SHA256(api_secret, query_string)
    - A 'timestamp' query parameter: current Unix epoch in milliseconds

  The signature payload is the raw query string (including timestamp and recvWindow)
  concatenated as key=value&key=value, then signed with the secret key using HMAC-SHA256.

References:
  https://binance-docs.github.io/apidocs/spot/en/#signed-trade-user_data-and-endpoints
"""

import hashlib
import hmac
import os
import time
from typing import Any

import httpx
from urllib.parse import urlencode

from utils.httpx_client import get_httpx_client
from utils.logging import get_logger

logger = get_logger(__name__)

# Base URLs for Binance REST API (Spot).
# Override via BINANCE_BASE_URL env var to point at the testnet (https://testnet.binance.vision).
BASE_URL = os.getenv("BINANCE_BASE_URL", "https://api.binance.com")

# Base URL for Binance USD-M Futures API.
# Override via BINANCE_FUTURES_URL env var.
FUTURES_URL = os.getenv("BINANCE_FUTURES_URL", "https://fapi.binance.com")

# Trade type constant — used by get_api_response to select Base vs Futures URL.
TRADE_TYPE_SPOT = "SPOT"
TRADE_TYPE_FUTURES = "FUTURES"


def generate_signature(api_secret: str, query_string: str) -> str:
    """
    Generate HMAC-SHA256 signature for Binance API requests.

    Binance signature formula:
        HMAC-SHA256(api_secret, query_string)

    Where query_string is the sorted key=value&key=value string
    including timestamp and recvWindow.

    Args:
        api_secret: The API secret key
        query_string: The raw query string to sign

    Returns:
        Hex-encoded HMAC-SHA256 digest
    """
    return hmac.new(
        bytes(api_secret, "utf-8"),
        bytes(query_string, "utf-8"),
        hashlib.sha256,
    ).hexdigest()


def get_url(endpoint: str, trade_type: str = TRADE_TYPE_SPOT) -> str:
    """
    Construct a full URL for a Binance API endpoint.

    Spot endpoints:   /api/v3/... → https://api.binance.com/api/v3/...
    Futures endpoints: /fapi/v1/... → https://fapi.binance.com/fapi/v1/...

    Args:
        endpoint: API path starting with '/', e.g. '/api/v3/order'
        trade_type: 'SPOT' or 'FUTURES'

    Returns:
        The complete URL
    """
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint

    if trade_type == TRADE_TYPE_FUTURES and FUTURES_URL:
        return FUTURES_URL + endpoint
    return BASE_URL + endpoint


def get_api_response(
    endpoint: str,
    api_key: str = None,
    api_secret: str = None,
    method: str = "GET",
    params: dict[str, Any] = None,
    payload: str = "",
    signed: bool = False,
    trade_type: str = TRADE_TYPE_SPOT,
) -> dict:
    """
    Make a request to the Binance REST API with optional HMAC-SHA256 signing.

    For signed endpoints (trading, account data):
        - The API key is sent in the X-MBX-APIKEY header
        - A 'timestamp' param is added to query string
        - A 'signature' param is computed from the sorted query string

    Args:
        endpoint:     API path e.g. '/api/v3/order'
        api_key:      Binance API key (from BROKER_API_KEY env var)
        api_secret:   Binance API secret (from BROKER_API_SECRET env var)
        method:       HTTP method (GET, POST, DELETE, PUT)
        params:       Dict of query / body parameters
        payload:      Raw JSON body string for POST/PUT requests
        signed:       Whether this endpoint requires authentication
        trade_type:   'SPOT' or 'FUTURES'

    Returns:
        Parsed JSON dict from Binance API.
        On error returns {"success": False, "error": {"code": ..., "message": ...}}
    """
    resolved_key = api_key or os.getenv("BROKER_API_KEY", "").strip()
    resolved_secret = api_secret or os.getenv("BROKER_API_SECRET", "").strip()

    # Build base URL
    url = get_url(endpoint, trade_type)

    # Build headers
    headers = {
        "User-Agent": "silvertrade-python-client",
        "Accept": "application/json",
    }

    # Build query string
    query_params = dict(params or {})

    if signed:
        if not resolved_key or not resolved_secret:
            return {"success": False, "error": {"code": "auth_error",
                    "message": "BROKER_API_KEY / BROKER_API_SECRET not configured"}}

        # Add timestamp and optional recvWindow
        query_params["timestamp"] = str(int(time.time() * 1000))
        query_params.setdefault("recvWindow", "5000")

        # Sign: sort keys, build query string, compute HMAC-SHA256
        query_string = urlencode(sorted(query_params.items()))
        query_params["signature"] = generate_signature(resolved_secret, query_string)

        # Set API key header
        headers["X-MBX-APIKEY"] = resolved_key

    # Build full URL with query params
    full_url = url
    if query_params:
        full_url = url + "?" + urlencode(sorted(query_params.items()))

    client = get_httpx_client()

    try:
        method_upper = method.upper()
        logger.debug(f"[Binance] {method_upper} {endpoint}")

        if method_upper == "GET":
            response = client.get(full_url, headers=headers)
        elif method_upper == "POST":
            ct_headers = dict(headers)
            if payload:
                ct_headers.setdefault("Content-Type", "application/json")
            response = client.post(
                full_url if not payload else url,
                headers=ct_headers,
                content=payload if payload else None,
                params=query_params if payload else None,
            )
        elif method_upper == "DELETE":
            response = client.request("DELETE", full_url, headers=headers)
        elif method_upper == "PUT":
            response = client.put(full_url, headers=headers)
        else:
            response = client.request(method_upper, full_url, headers=headers)

    except Exception as e:
        logger.error(f"[Binance] Request error: {e}")
        return {"success": False, "error": {"code": "request_error", "message": str(e)}}

    logger.debug(f"[Binance] HTTP {response.status_code} from {endpoint}")

    if not response.text.strip():
        return {"success": False, "error": {"code": "empty_response",
                "message": f"Empty response from {endpoint}"}}

    try:
        data = response.json()
    except Exception as e:
        logger.error(f"[Binance] JSON parse error: {e} — body: {response.text[:300]}")
        return {"success": False, "error": {"code": "json_parse_error", "message": str(e)}}

    # Binance returns error codes in the 400+ range with an 'code' and 'msg' field
    if response.status_code not in (200, 201):
        err_code = data.get("code", response.status_code)
        err_msg = data.get("msg", response.text[:200])
        logger.error(f"[Binance] HTTP {response.status_code} code={err_code}: {err_msg}")
        return {"success": False, "error": {"code": err_code, "message": err_msg}}

    return {"success": True, "result": data}
