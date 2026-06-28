"""
Shared httpx client module with connection pooling support for all broker APIs
with automatic protocol negotiation (HTTP/2 when available, HTTP/1.1 fallback)
"""

from typing import Any, Optional

import httpx

from utils.circuit_breaker import (
    CircuitBreakerOpenError,
    get_circuit_breaker,
    retry_with_backoff,
)
from utils.logging import get_logger

# Set up logging
logger = get_logger(__name__)

# ── Broker URL → breaker-name mapping ────────────────────────────────
# Used by ``request_with_circuit_breaker()`` to auto-detect which circuit
# breaker to use based on the request URL.  When no pattern matches the
# call falls back to a shared ``"broker_http"`` breaker.
_BROKER_PATTERNS: dict[str, str] = {
    "api.kite.trade": "zerodha",
    "apiconnect.angelone": "angel",
    "api-t1.fyers": "fyers",
    "api.upstox": "upstox",
    "api.shoonya": "shoonya",
    "api.paytmmoney": "paytm",
    "openapi.5paisa": "fivepaisa",
    "gw-napi.kotaksecurities": "kotak",
    "api.dhan": "dhan",
    "api.flattrade": "flattrade",
    "api.aliceblueonline": "aliceblue",
    "delta.exchange": "deltaexchange",
    "api.binance": "binance",
    "api-v2.zerodha": "zerodha_v2",
    "trade.jainam": "jainam",
    "mstock": "mstock",
    "sbizone": "definedge",
    "icicidirect": "icici",
    "iifl": "iifl",
    "motilal": "motilal",
}


def _detect_broker(url: str) -> str:
    """Extract a breaker-friendly broker name from *url*, or ``"broker_http"``."""
    from urllib.parse import urlparse

    hostname = urlparse(url).hostname or ""
    for pattern, name in _BROKER_PATTERNS.items():
        if pattern in hostname:
            return name
    return "broker_http"


# Global httpx client for connection pooling
_httpx_client = None


def get_httpx_client() -> httpx.Client:
    """
    Returns an HTTP client with automatic protocol negotiation.
    The client will use HTTP/2 when the server supports it,
    otherwise automatically falls back to HTTP/1.1.

    Returns:
        httpx.Client: A configured HTTP client with protocol auto-negotiation
    """
    global _httpx_client

    if _httpx_client is None:
        _httpx_client = _create_http_client()
        logger.info(
            "Created HTTP client with automatic protocol negotiation (HTTP/2 preferred, HTTP/1.1 fallback)"
        )
    return _httpx_client


def request(method: str, url: str, **kwargs) -> httpx.Response:
    """
    Make an HTTP request using the shared client with automatic protocol negotiation.

    Args:
        method: HTTP method (GET, POST, etc.)
        url: URL to request
        **kwargs: Additional arguments to pass to the request

    Returns:
        httpx.Response: The HTTP response

    Raises:
        httpx.HTTPError: If the request fails
    """
    import time

    from flask import g

    client = get_httpx_client()

    # Detect broker name from URL for metrics
    broker_name = _detect_broker(url)

    # Track actual broker API call time for latency monitoring
    broker_api_start = time.time()
    response = client.request(method, url, **kwargs)
    broker_api_end = time.time()

    broker_latency = broker_api_end - broker_api_start

    # Record Prometheus metrics
    try:
        from blueprints.metrics import broker_latency_observe, broker_request_inc

        broker_request_inc(broker_name, method, response.status_code)
        broker_latency_observe(broker_name, method, broker_latency)
    except ImportError:
        pass
    except Exception:
        pass

    # Store broker API time in Flask's g object for latency tracking
    if hasattr(g, "latency_tracker"):
        broker_api_time_ms = broker_latency * 1000
        g.broker_api_time = broker_api_time_ms
        logger.debug(f"Broker API call took {broker_api_time_ms:.2f}ms")

    # Log the actual HTTP version used (info level for visibility)
    if response.http_version:
        logger.debug(f"Request used {response.http_version} - URL: {url[:50]}...")

    return response


# Shortcut methods for common HTTP methods
def get(url: str, **kwargs) -> httpx.Response:
    """
    Send a GET request.

    Args:
        url (str): The URL to send the GET request to.
        **kwargs: Additional arguments passed to the underlying request method.

    Returns:
        httpx.Response: The HTTP response from the server.
    """
    return request("GET", url, **kwargs)


def post(url: str, **kwargs) -> httpx.Response:
    """
    Send a POST request.

    Args:
        url (str): The URL to send the POST request to.
        **kwargs: Additional arguments passed to the underlying request method.

    Returns:
        httpx.Response: The HTTP response from the server.
    """
    return request("POST", url, **kwargs)


def put(url: str, **kwargs) -> httpx.Response:
    """
    Send a PUT request.

    Args:
        url (str): The URL to send the PUT request to.
        **kwargs: Additional arguments passed to the underlying request method.

    Returns:
        httpx.Response: The HTTP response from the server.
    """
    return request("PUT", url, **kwargs)


def delete(url: str, **kwargs) -> httpx.Response:
    """
    Send a DELETE request.

    Args:
        url (str): The URL to send the DELETE request to.
        **kwargs: Additional arguments passed to the underlying request method.

    Returns:
        httpx.Response: The HTTP response from the server.
    """
    return request("DELETE", url, **kwargs)


def _create_http_client() -> httpx.Client:
    """
    Create a new HTTP client with automatic protocol negotiation and latency tracking.
    Enables both HTTP/2 and HTTP/1.1, letting httpx choose the best protocol.

    Returns:
        httpx.Client: A configured HTTP client with protocol auto-negotiation and timing hooks
    """
    import os
    import time

    from flask import g

    # Event hooks for tracking broker API timing
    def log_request(request):
        """Hook called before request is sent"""
        request.extensions["start_time"] = time.time()
        logger.debug(f"Starting request to {request.url}")

    def log_response(response):
        """Hook called after response is received"""
        try:
            start_time = response.request.extensions.get("start_time")
            if start_time:
                duration_ms = (time.time() - start_time) * 1000

                # Store broker API time in Flask's g object for latency tracking
                try:
                    from flask import has_request_context

                    if has_request_context() and hasattr(g, "latency_tracker"):
                        g.broker_api_time = duration_ms
                        logger.debug(f"Broker API call took {duration_ms:.2f}ms")
                except (RuntimeError, AttributeError):
                    # Not in Flask request context or g not available
                    pass

                logger.debug(f"Request completed in {duration_ms:.2f}ms")
        except Exception as e:
            logger.exception(f"Error in response hook: {e}")

    try:
        # Detect if running in standalone mode (Docker/production) vs integrated mode (local dev)
        # In standalone mode, disable HTTP/2 to avoid protocol negotiation issues
        app_mode = os.environ.get("APP_MODE", "integrated").strip().strip("'\"")
        is_standalone = app_mode == "standalone"

        # Disable HTTP/2 in standalone/Docker environments to avoid protocol negotiation issues
        http2_enabled = not is_standalone

        client = httpx.Client(
            http2=http2_enabled,  # Disable HTTP/2 in standalone mode, enable in integrated mode
            http1=True,  # Always enable HTTP/1.1 for compatibility
            timeout=120.0,  # Increased timeout for large historical data requests
            limits=httpx.Limits(
                max_keepalive_connections=40,  # Increased from 20 for multi-strategy environments
                max_connections=100,  # Increased from 50 for 10+ concurrent strategies
                keepalive_expiry=30.0,  # Reduced from 120s to recycle stale connections faster
            ),
            # Add verify parameter to handle SSL/TLS issues in standalone mode
            verify=True,  # Can be set to False for debugging SSL issues (not recommended for production)
            # Add event hooks for latency tracking
            event_hooks={"request": [log_request], "response": [log_response]},
        )

        if is_standalone:
            logger.info("Running in standalone mode - HTTP/2 disabled for compatibility")
        else:
            logger.info("Running in integrated mode - HTTP/2 enabled for optimal performance")

        return client

    except Exception as e:
        logger.exception(f"Failed to create HTTP client: {e}")
        raise


# ── Circuit Breaker + Retry Integration ─────────────────────────────────


def request_with_circuit_breaker(
    method: str,
    url: str,
    *,
    breaker_name: str | None = None,
    retry_enabled: bool = True,
    max_retries: int = 2,
    breaker_failure_threshold: int = 5,
    breaker_recovery_timeout: float = 30.0,
    **kwargs: Any,
) -> httpx.Response:
    """Make an HTTP request protected by a circuit breaker + optional retry.

    This is the recommended way to make broker HTTP calls.  It wraps the
    shared ``request()`` function with:

    1. :class:`CircuitBreaker` — fail-fast when a broker is unhealthy,
       preventing cascading timeouts from blocking request handler threads.
    2. :func:`retry_with_backoff` — transparently retry transient failures
       (connection drops, timeouts, 5xx) before giving up.

    Parameters
    ----------
    method : str
        HTTP method (``GET``, ``POST``, etc.).
    url : str
        Request URL.
    breaker_name : str or None
        Circuit breaker name.  Auto-detected from URL when ``None``.
    retry_enabled : bool
        Whether to apply retry-with-exponential-backoff (default ``True``).
    max_retries : int
        Maximum retry attempts before giving up (default ``2``).
    breaker_failure_threshold : int
        Consecutive failures to trip the circuit OPEN (default ``5``).
    breaker_recovery_timeout : float
        Seconds before OPEN→HALF_OPEN transition (default ``30``).
    **kwargs
        Forwarded to ``request()``.

    Returns
    -------
    httpx.Response

    Raises
    ------
    CircuitBreakerOpenError
        When the circuit is OPEN and the request is rejected.
    httpx.HTTPError
        When the request fails and retries are exhausted (or disabled).
    """
    if breaker_name is None:
        breaker_name = _detect_broker(url)

    breaker = get_circuit_breaker(
        breaker_name,
        failure_threshold=breaker_failure_threshold,
        recovery_timeout=breaker_recovery_timeout,
    )

    # Check if the circuit is OPEN before even attempting
    if breaker.is_open():
        raise CircuitBreakerOpenError(
            breaker.name, breaker.state, breaker.stats().get("retry_after")
        )

    def _do_request() -> httpx.Response:
        # The breaker's call() will record success/failure
        return breaker.call(request, method, url, **kwargs)

    if retry_enabled:
        result, attempts = retry_with_backoff(
            _do_request,
            max_retries=max_retries,
            base_delay=0.5,
            max_delay=10.0,
            retryable_exceptions=(
                ConnectionError,
                TimeoutError,
                OSError,
                httpx.TimeoutException,
                httpx.ConnectError,
                httpx.RemoteProtocolError,
                httpx.TransportError,
            ),
        )
        return result

    return _do_request()


def cleanup_httpx_client() -> None:
    """
    Closes the global httpx client and releases its resources.

    Should be called when the application is shutting down to prevent
    resource leaks.

    Returns:
        None
    """
    global _httpx_client

    if _httpx_client is not None:
        _httpx_client.close()
        _httpx_client = None
        logger.info("Closed HTTP client")
