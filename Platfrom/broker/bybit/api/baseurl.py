"""
Bybit API Base URL Configuration and HMAC-SHA256 Signing.

Authentication:
  Bybit uses HMAC-SHA256 signed headers for private endpoints.
  Required headers:
    X-BAPI-API-KEY     — API Key
    X-BAPI-TIMESTAMP   — Current UTC timestamp in milliseconds (string)
    X-BAPI-RECV-WINDOW — Validation time window in milliseconds (default 5000)
    X-BAPI-SIGN        — HMAC-SHA256 signature (lowercase hex)

  Signature formula:
    GET:  timestamp + API_KEY + RECV_WINDOW + queryString
    POST: timestamp + API_KEY + RECV_WINDOW + jsonBodyString

  The server validates that the timestamp is within:
    [server_time - recv_window, server_time + 1000)

  Response format (all endpoints):
    {
      "retCode": 0,
      "retMsg": "OK",
      "result": { ... },
      "retExtInfo": {},
      "time": 1671017382656
    }
    retCode == 0 means success. Non-zero means an error.

References:
  https://bybit-exchange.github.io/docs/v5/guide
"""

import hashlib
import hmac
import json
import os
import time
from typing import Any
from urllib.parse import urlencode

from utils.httpx_client import request_with_circuit_breaker
from utils.logging import get_logger

logger = get_logger(__name__)

# Base URL for Bybit REST API (mainnet).
# Override via BYBIT_BASE_URL env var to point at testnet (https://api-testnet.bybit.com).
BASE_URL = os.getenv("BYBIT_BASE_URL", "https://api.bybit.com")

# Trade type constants.
TRADE_TYPE_SPOT = "spot"
TRADE_TYPE_LINEAR = "linear"  # USDT perpetual futures


def generate_signature(api_secret: str, payload: str) -> str:
    """
    Generate HMAC-SHA256 signature for Bybit API requests.

    Args:
        api_secret: The API secret key
        payload: Prehash string (depends on HTTP method)

    Returns:
        Lowercase hex-encoded HMAC-SHA256 digest
    """
    return hmac.new(
        bytes(api_secret, "utf-8"),
        bytes(payload, "utf-8"),
        hashlib.sha256,
    ).hexdigest()


def get_url(endpoint: str) -> str:
    """
    Construct a full URL for a Bybit API endpoint.

    Args:
        endpoint: API path starting with '/', e.g. '/v5/order/create'

    Returns:
        The complete URL
    """
    if not endpoint.startswith("/"):
        endpoint = "/" + endpoint
    return BASE_URL + endpoint


def get_auth_headers(
    api_key: str,
    timestamp: str,
    recv_window: str,
    signature: str,
) -> dict[str, str]:
    """
    Build the authentication headers for a Bybit API request.

    Args:
        api_key:     Bybit API key
        timestamp:   Current UTC timestamp in milliseconds (string)
        recv_window: Validation window (string, e.g. "5000")
        signature:   HMAC-SHA256 hex digest

    Returns:
        Dict of headers ready to pass to httpx
    """
    return {
        "X-BAPI-API-KEY": api_key,
        "X-BAPI-TIMESTAMP": timestamp,
        "X-BAPI-RECV-WINDOW": recv_window,
        "X-BAPI-SIGN": signature,
        "User-Agent": "silvertrade-python-client",
        "Content-Type": "application/json",
        "Accept": "application/json",
    }


def get_api_response(
    endpoint: str,
    api_key: str = None,
    api_secret: str = None,
    method: str = "GET",
    params: dict[str, Any] = None,
    body: dict[str, Any] = None,
    signed: bool = False,
    category: str = TRADE_TYPE_SPOT,
) -> dict:
    """
    Make a request to the Bybit REST API with optional HMAC-SHA256 signing.

    For signed endpoints:
        - Headers include X-BAPI-API-KEY, X-BAPI-TIMESTAMP, X-BAPI-RECV-WINDOW, X-BAPI-SIGN
        - Signature formula:
            GET:  timestamp + API_KEY + RECV_WINDOW + queryString
            POST: timestamp + API_KEY + RECV_WINDOW + jsonBodyString

    Args:
        endpoint:   API path e.g. '/v5/order/create'
        api_key:    Bybit API key (from BROKER_API_KEY)
        api_secret: Bybit API secret (from BROKER_API_SECRET)
        method:     HTTP method (GET, POST)
        params:     Dict of query parameters (GET requests)
        body:       Dict of body parameters (POST requests)
        signed:     Whether this endpoint requires authentication
        category:   Trade category ('spot' | 'linear')

    Returns:
        Parsed JSON dict from Bybit API.
        On error returns {"success": False, "error": {"code": ..., "message": ...}}
    """
    resolved_key = api_key or os.getenv("BROKER_API_KEY", "").strip()
    resolved_secret = api_secret or os.getenv("BROKER_API_SECRET", "").strip()

    # Add category to params if not already present
    params = dict(params or {})
    if category and "category" not in params:
        params["category"] = category

    # Build URL
    url = get_url(endpoint)

    # Build query string for GET or body JSON string for POST
    method_upper = method.upper()

    # Common headers
    headers = {
        "User-Agent": "silvertrade-python-client",
        "Accept": "application/json",
    }

    if signed:
        if not resolved_key or not resolved_secret:
            return {
                "success": False,
                "error": {
                    "code": "auth_error",
                    "message": "BROKER_API_KEY / BROKER_API_SECRET not configured",
                },
            }

        timestamp = str(int(time.time() * 1000))
        recv_window = "5000"

        if method_upper == "GET":
            # Build query string (sorted keys)
            query_string = urlencode(sorted(params.items())) if params else ""
            # Signature payload: timestamp + API_KEY + RECV_WINDOW + queryString
            sign_payload = timestamp + resolved_key + recv_window + query_string
            if query_string:
                url = url + "?" + query_string
        else:
            # POST: signature payload: timestamp + API_KEY + RECV_WINDOW + jsonBodyString
            body = body or {}
            json_body = json.dumps(body, separators=(",", ":"))
            sign_payload = timestamp + resolved_key + recv_window + json_body

        signature = generate_signature(resolved_secret, sign_payload)
        auth_headers = get_auth_headers(resolved_key, timestamp, recv_window, signature)
        headers.update(auth_headers)

    try:
        logger.debug(f"[Bybit] {method_upper} {endpoint}")

        if method_upper == "GET":
            response = request_with_circuit_breaker("GET", url, headers=headers)
        elif method_upper == "POST":
            if body is not None:
                headers["Content-Type"] = "application/json"
                response = request_with_circuit_breaker("POST", url, headers=headers, json=body)
            else:
                response = request_with_circuit_breaker("POST", url, headers=headers)
        else:
            response = request_with_circuit_breaker(method_upper, url, headers=headers)

    except Exception as e:
        logger.error(f"[Bybit] Request error: {e}")
        return {"success": False, "error": {"code": "request_error", "message": str(e)}}

    logger.debug(f"[Bybit] HTTP {response.status_code} from {endpoint}")

    if not response.text.strip():
        return {
            "success": False,
            "error": {"code": "empty_response", "message": f"Empty response from {endpoint}"},
        }

    try:
        data = response.json()
    except Exception as e:
        logger.error(f"[Bybit] JSON parse error: {e} — body: {response.text[:300]}")
        return {"success": False, "error": {"code": "json_parse_error", "message": str(e)}}

    # Bybit response envelope: retCode == 0 means success
    ret_code = data.get("retCode", -1)
    ret_msg = data.get("retMsg", "")

    if ret_code == 0:
        return {"success": True, "result": data.get("result", {})}
    else:
        logger.error(f"[Bybit] API error (code={ret_code}): {ret_msg}")
        return {"success": False, "error": {"code": ret_code, "message": ret_msg}}
