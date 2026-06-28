"""
Order Safety — wraps broker API calls with automatic reversal on failure.

Core principle:
  1. Call broker (money leaves user)
  2. If broker succeeds → process the result (log, publish events)
  3. If processing fails → REVERSE at broker immediately
  4. If reversal also fails → CRITICAL alert (engineer must intervene)

Usage in a service::

    from utils.order_safety import safe_place_order

    success, response, status_code = safe_place_order(
        broker_func=lambda: broker_module.place_order_api(order_data, auth_token),
        cancel_func=lambda oid: broker_module.cancel_order(oid, auth_token),
        on_success=lambda oid: bus.publish(OrderPlacedEvent(...)),
        order_ref=order_data.get("symbol", "unknown"),
        api_key=api_key,
    )
"""

import os
import sys
import traceback
from typing import Any, Callable

from utils.logging import get_logger

logger = get_logger(__name__)

# Emergency contact method — override via env var if you have a real endpoint.
# In production this should point to PagerDuty, OpsGenie, or a Slack webhook.
_EMERGENCY_WEBHOOK = os.getenv(
    "ORDER_SAFETY_EMERGENCY_WEBHOOK",
    "",  # Default: log only (no external alert)
)


def _emergency_alert(message: str, order_ref: str, api_key: str = "") -> None:
    """Fire a CRITICAL alert that an order cannot be reversed.

    Logs at CRITICAL level. If ORDER_SAFETY_EMERGENCY_WEBHOOK is set, also
    fires an HTTP POST to that endpoint so on-call engineers get paged.
    """
    full_msg = (
        f"🚨 EMERGENCY: ORPHANED ORDER — {message} [ref={order_ref}, api_key={api_key[:8]}...]"
    )
    logger.critical(full_msg)

    if _EMERGENCY_WEBHOOK:
        try:
            import requests

            if not _EMERGENCY_WEBHOOK.startswith("https://"):
                logger.error(f"Emergency webhook URL must use HTTPS: {_EMERGENCY_WEBHOOK[:30]}...")
                return

            try:
                requests.post(
                    _EMERGENCY_WEBHOOK,
                    json={
                        "text": full_msg,
                        "order_ref": order_ref,
                        "severity": "critical",
                        "source": "order_safety",
                    },
                    timeout=5,
                )
            except requests.exceptions.RequestException as e:
                logger.error(f"Failed to fire emergency webhook: {e}")
        except Exception as e:
            logger.error(f"Failed to fire emergency webhook: {e}")


def safe_place_order(
    *,
    broker_func: Callable[[], tuple[Any, dict[str, Any], str]],
    cancel_func: Callable[[str], tuple[Any, int]],
    on_success: Callable[[str], None],
    order_ref: str,
    api_key: str = "",
) -> tuple[bool, dict[str, Any], int]:
    """
    Place an order with automatic reversal on processing failure.

    Parameters
    ----------
    broker_func:
        Zero-argument callable that invokes ``broker_module.place_order_api``.
        Returns ``(response_shim, response_dict, order_id)``.
    cancel_func:
        Single-argument callable ``(order_id)`` that invokes
        ``broker_module.cancel_order``. Returns ``(response, status_code)``.
    on_success:
        Single-argument callable ``(order_id)`` called after the broker
        confirms success. If this raises, the order is reversed.
    order_ref:
        Human-readable reference for logs (e.g. ``"RELIANCE_BUY_100"``).
    api_key:
        Truncated for emergency alerts.

    Returns
    -------
    ``(success, response_data, http_status)``
    """
    # ---- Step 1: Call broker ----
    try:
        res, response_data, order_id = broker_func()
    except Exception as e:
        logger.error(f"Broker API call failed for {order_ref}: {e}")
        return (
            False,
            {"status": "error", "message": "Failed to place order due to broker error"},
            500,
        )

    # ---- Step 2: Broker rejected the order ----
    is_success = _is_successful(res)
    if not is_success:
        msg = (
            response_data.get("message", "Broker rejected the order")
            if isinstance(response_data, dict)
            else "Broker rejected the order"
        )
        return False, {"status": "error", "message": msg}, _extract_status(res, 400)

    # ---- Step 3: Broker accepted — run on_success callback ----
    try:
        on_success(order_id)
    except Exception as e:
        # CRITICAL: Broker has our money but our internal processing failed.
        # We MUST try to reverse the order at the broker.
        logger.critical(
            "CRITICAL: Order %s succeeded at broker but post-processing failed: %s. "
            "Attempting reversal...",
            order_ref,
            e,
        )
        _attempt_reversal(
            order_id=order_id,
            cancel_func=cancel_func,
            order_ref=order_ref,
            api_key=api_key,
        )
        # on_success also fired the event — we cannot undo that.
        # Return a user-facing error so they retry.
        return (
            False,
            {
                "status": "error",
                "message": "Order placed at broker but internal processing failed. "
                "If not reversed automatically, contact support with reference: "
                f"{order_id}",
            },
            500,
        )

    # ---- Everything succeeded ----
    return True, {"status": "success", "orderid": str(order_id)}, 200


def _is_successful(res: Any) -> bool:
    """Check if a broker response indicates success.

    Handles both object-style (``res.status``) and dict-style
    (``res["status"]``) responses across all 30+ broker plugins.
    """
    if res is None:
        return False
    if hasattr(res, "status"):
        return res.status == 200
    if isinstance(res, dict):
        return res.get("status") in (200, "success", True)
    return bool(res)


def _extract_status(res: Any, default: int = 400) -> int:
    """Extract HTTP status from broker response, defaulting to *default*."""
    if hasattr(res, "status"):
        return int(res.status)
    if isinstance(res, dict):
        return int(res.get("status", default))
    return default


def _attempt_reversal(
    *,
    order_id: str,
    cancel_func: Callable[[str], tuple[Any, int]],
    order_ref: str,
    api_key: str = "",
) -> None:
    """Attempt to cancel the order at the broker.

    If reversal fails, fires an emergency alert — an engineer MUST intervene
    to manually verify and close the position before end of day.
    """
    try:
        cancel_res, cancel_status = cancel_func(order_id)
        if cancel_status == 200:
            logger.info(
                "ORDER SUCCESSFULLY REVERSED: %s (order_id=%s)",
                order_ref,
                order_id,
            )
        else:
            _emergency_alert(
                f"Reversal ATTEMPTED but broker returned status {cancel_status}. "
                f"Order {order_id} for {order_ref} may still be live.",
                order_ref,
                api_key,
            )
    except Exception as e:
        _emergency_alert(
            f"Reversal FAILED with exception: {e}. "
            f"Order {order_id} for {order_ref} is ORPHANED — manual intervention required!",
            order_ref,
            api_key,
        )
