"""
Structured Error System — replaces all raw ``str(e)`` and ``traceback``
leaks in API responses with safe, standardized error payloads.

Every error returned to the API consumer now includes:
  - ``error_code``   — machine-readable identifier (ST-0001 ... ST-9999)
  - ``message``      — user-safe, human-readable description
  - ``correlation_id`` — log correlation ID for support debugging
  - ``support_url``  — link to docs/troubleshooting (if configured)

Internal exception details (traceback, internal variable values) are
logged server-side via ``logger.exception()`` and NEVER sent to the client.

Usage in blueprints::

    from utils.errors import APIError, ErrorCode, safe_error_response

    # Instead of:  return {"status": "error", "message": str(e)}, 500
    # Use:
    logger.exception("Failed to place order")
    return safe_error_response(ErrorCode.INTERNAL_ERROR), 500

Or raise an APIError and let the error handler catch it::

    raise APIError(ErrorCode.VALIDATION_ERROR, "Invalid exchange")
"""

import uuid
from enum import Enum
from typing import Any, Optional


class ErrorCode(str, Enum):
    """Canonical error codes used across all API responses.

    Format: ST-XXXX where ST = SilverTrade and XXXX = sequential number.
    Ranges:
        ST-0001 – ST-0999  Authentication & Authorization
        ST-1000 – ST-1999  Validation
        ST-2000 – ST-2999  Broker errors
        ST-3000 – ST-3999  Database errors
        ST-4000 – ST-4999  Rate limiting & Quota
        ST-5000 – ST-5999  Internal / System errors
        ST-9000 – ST-9999  Reserved for emergencies
    """

    # ── Auth (0001-0999) ────────────────────────────────────────────────
    AUTH_REQUIRED = "ST-0001"
    AUTH_INVALID_API_KEY = "ST-0002"
    AUTH_TOKEN_EXPIRED = "ST-0003"
    AUTH_TOKEN_REVOKED = "ST-0004"
    AUTH_FORBIDDEN = "ST-0005"
    AUTH_SESSION_EXPIRED = "ST-0006"
    AUTH_RATE_LIMITED = "ST-0007"

    # ── Validation (1000-1999) ──────────────────────────────────────────
    VALIDATION_ERROR = "ST-1000"
    VALIDATION_MISSING_FIELD = "ST-1001"
    VALIDATION_INVALID_EXCHANGE = "ST-1002"
    VALIDATION_INVALID_ACTION = "ST-1003"
    VALIDATION_INVALID_SYMBOL = "ST-1004"
    VALIDATION_INVALID_QUANTITY = "ST-1005"
    VALIDATION_INVALID_PRICE = "ST-1006"

    # ── Broker (2000-2999) ──────────────────────────────────────────────
    BROKER_ERROR = "ST-2000"
    BROKER_MODULE_NOT_FOUND = "ST-2001"
    BROKER_ORDER_REJECTED = "ST-2002"
    BROKER_TIMEOUT = "ST-2003"
    BROKER_INSUFFICIENT_FUNDS = "ST-2004"
    BROKER_POSITION_NOT_FOUND = "ST-2005"
    BROKER_REVERSAL_FAILED = "ST-2006"

    # ── Database (3000-3999) ────────────────────────────────────────────
    DB_ERROR = "ST-3000"
    DB_CONNECTION_FAILED = "ST-3001"
    DB_QUERY_FAILED = "ST-3002"
    DB_DATA_NOT_FOUND = "ST-3003"

    # ── Rate Limiting (4000-4999) ───────────────────────────────────────
    RATE_LIMIT_EXCEEDED = "ST-4000"
    RATE_LIMIT_IP_BANNED = "ST-4001"

    # ── System / Internal (5000-5999) ───────────────────────────────────
    INTERNAL_ERROR = "ST-5000"
    SERVICE_UNAVAILABLE = "ST-5001"
    SHUTTING_DOWN = "ST-5002"
    FEATURE_NOT_AVAILABLE = "ST-5003"

    # ── Emergency (9000-9999) ───────────────────────────────────────────
    EMERGENCY_ORPHANED_ORDER = "ST-9000"
    EMERGENCY_DATA_LOSS = "ST-9001"


# User-safe message templates (no internal details exposed)
_ERROR_MESSAGES: dict[ErrorCode, str] = {
    ErrorCode.AUTH_REQUIRED: "Authentication is required. Please provide a valid API key.",
    ErrorCode.AUTH_INVALID_API_KEY: "The provided API key is invalid. Check your key and try again.",
    ErrorCode.AUTH_TOKEN_EXPIRED: "Session has expired. Please log in again.",
    ErrorCode.AUTH_TOKEN_REVOKED: "Your session has been revoked. Please log in again.",
    ErrorCode.AUTH_FORBIDDEN: "You do not have permission to perform this action.",
    ErrorCode.AUTH_SESSION_EXPIRED: "Your session has expired due to inactivity.",
    ErrorCode.AUTH_RATE_LIMITED: "Too many requests. Please wait before trying again.",
    ErrorCode.VALIDATION_ERROR: "The request contains invalid data.",
    ErrorCode.VALIDATION_MISSING_FIELD: "A required field is missing from the request.",
    ErrorCode.VALIDATION_INVALID_EXCHANGE: "The specified exchange is not supported.",
    ErrorCode.VALIDATION_INVALID_ACTION: "The specified action is not valid. Use BUY or SELL.",
    ErrorCode.VALIDATION_INVALID_SYMBOL: "The specified symbol is not recognized.",
    ErrorCode.VALIDATION_INVALID_QUANTITY: "Quantity must be a positive number.",
    ErrorCode.VALIDATION_INVALID_PRICE: "Price must be a non-negative number.",
    ErrorCode.BROKER_ERROR: "An error occurred while communicating with the broker.",
    ErrorCode.BROKER_MODULE_NOT_FOUND: "The broker is not configured or not supported.",
    ErrorCode.BROKER_ORDER_REJECTED: "The broker rejected the order.",
    ErrorCode.BROKER_TIMEOUT: "The broker did not respond in time. Please try again.",
    ErrorCode.BROKER_INSUFFICIENT_FUNDS: "Insufficient funds or margin for this order.",
    ErrorCode.BROKER_POSITION_NOT_FOUND: "The specified position was not found.",
    ErrorCode.BROKER_REVERSAL_FAILED: "An order was placed but could not be confirmed. Contact support.",
    ErrorCode.DB_ERROR: "A database error occurred. Please try again.",
    ErrorCode.DB_CONNECTION_FAILED: "Could not connect to the database.",
    ErrorCode.DB_QUERY_FAILED: "A database query failed. Please try again.",
    ErrorCode.DB_DATA_NOT_FOUND: "The requested data was not found.",
    ErrorCode.RATE_LIMIT_EXCEEDED: "Rate limit exceeded. Please slow down your requests.",
    ErrorCode.RATE_LIMIT_IP_BANNED: "Your IP has been temporarily banned due to suspicious activity.",
    ErrorCode.INTERNAL_ERROR: "An internal error occurred. If the problem persists, contact support.",
    ErrorCode.SERVICE_UNAVAILABLE: "Service is temporarily unavailable. Please try again later.",
    ErrorCode.SHUTTING_DOWN: "Server is shutting down. Please retry your request.",
    ErrorCode.FEATURE_NOT_AVAILABLE: "This feature is not available.",
    ErrorCode.EMERGENCY_ORPHANED_ORDER: "CRITICAL: Order may be orphaned. Contact support immediately.",
    ErrorCode.EMERGENCY_DATA_LOSS: "CRITICAL: Data may have been lost. Contact support immediately.",
}


class APIError(Exception):
    """An error that can be safely returned to the API consumer.

    All internal details are logged server-side. The client only sees
    the error code, user-safe message, and correlation ID.

    Usage::

        raise APIError(ErrorCode.VALIDATION_ERROR, "Invalid exchange")
    """

    def __init__(
        self,
        code: ErrorCode,
        message: Optional[str] = None,
        *,
        correlation_id: Optional[str] = None,
        status_code: int = 400,
        details: Optional[dict[str, Any]] = None,
    ) -> None:
        self.code = code
        self.message = message or _ERROR_MESSAGES.get(code, "An unknown error occurred.")
        self.correlation_id = correlation_id or uuid.uuid4().hex[:12]
        self.status_code = status_code
        self.details = details or {}
        super().__init__(self.message)

    def to_dict(self) -> dict[str, Any]:
        """Serialize to a safe API response dict."""
        result: dict[str, Any] = {
            "status": "error",
            "error_code": self.code.value,
            "message": self.message,
            "correlation_id": self.correlation_id,
        }
        if self.details:
            result["details"] = self.details
        return result


def safe_error_response(
    code: ErrorCode,
    message: Optional[str] = None,
    *,
    correlation_id: Optional[str] = None,
    status_code: int = 400,
    details: Optional[dict[str, Any]] = None,
) -> tuple[dict[str, Any], int]:
    """Create a safe, structured error response tuple ``(dict, http_status)``.

    This is the recommended replacement for raw ``return {..., \"message\": str(e)}, 500``.

    Example::

        return safe_error_response(ErrorCode.BROKER_ERROR, status_code=500)
    """
    err = APIError(
        code=code,
        message=message,
        correlation_id=correlation_id,
        status_code=status_code,
        details=details,
    )
    return err.to_dict(), err.status_code
