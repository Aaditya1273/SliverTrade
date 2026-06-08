"""
Server-side plan capacity enforcement.

Provides decorators and inline helpers to check whether the current user's
plan has remaining capacity for a given resource (strategies, workflows, etc.)
before the request proceeds.

Usage as decorator:
    @strategy_bp.route("/api/strategy", methods=["POST"])
    @check_session_validity
    @check_plan_capacity("active_strategies", count_strategies)
    def api_create_strategy():
        ...

Usage inline:
    from utils.plan_limits import check_capacity_or_error

    ok, response = check_capacity_or_error("flow_workflows", count_workflows(user_id))
    if not ok:
        return response
"""

from functools import wraps

from flask import jsonify, session

from database.user_db import User
from utils.logging import get_logger

logger = get_logger(__name__)

# ── Plan-level feature limits ────────────────────────────────────────────
# Server-side source of truth. The frontend PLANS array should match for
# display. Moved here from the billing blueprint to avoid circular imports
# when used by other blueprints.

PLAN_LIMITS = {
    "free": {
        "signals_per_month": 50,
        "active_strategies": 1,
        "python_strategies": 0,
        "chartink_strategies": 1,
        "flow_workflows": 1,
        "api_rate_limit": "20 per minute",
        "has_telegram_charts": False,
        "has_option_chain": False,
        "has_python_engine": False,
        "has_flow_editor": False,
        "has_multiple_brokers": False,
        "has_advanced_analytics": False,
        "has_dedicated_support": False,
    },
    "pro": {
        "signals_per_month": 10000,
        "active_strategies": None,  # unlimited
        "python_strategies": 10,
        "chartink_strategies": None,  # unlimited
        "flow_workflows": 10,
        "api_rate_limit": "60 per minute",
        "has_telegram_charts": True,
        "has_option_chain": True,
        "has_python_engine": True,
        "has_flow_editor": True,
        "has_multiple_brokers": False,
        "has_advanced_analytics": True,
        "has_dedicated_support": False,
    },
    "enterprise": {
        "signals_per_month": None,  # unlimited
        "active_strategies": None,  # unlimited
        "python_strategies": None,  # unlimited
        "chartink_strategies": None,  # unlimited
        "flow_workflows": None,  # unlimited
        "api_rate_limit": "120 per minute",
        "has_telegram_charts": True,
        "has_option_chain": True,
        "has_python_engine": True,
        "has_flow_editor": True,
        "has_multiple_brokers": True,
        "has_advanced_analytics": True,
        "has_dedicated_support": True,
    },
}


# ── Convenience helpers: count resources per user ─────────────────────────


def check_signal_capacity_for_user(user_id: str):
    """
    Check if a user has remaining signal capacity for this month.
    Session-independent — designed for webhook handlers where there is no Flask session.

    Does NOT increment the counter; that's done by ``increment_signal_usage``
    after the signal is successfully processed.

    Returns:
        ``(True, None)`` if there is capacity.
        ``(False, (jsonify_response, status_code))`` if the limit is exceeded.
    """
    user = User.query.get(user_id)
    if not user:
        return False, (jsonify({"status": "error", "message": "User not found"}), 404)

    plan = user.plan or "free"
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
    max_signals = limits.get("signals_per_month")

    # null = unlimited
    if max_signals is None:
        return True, None

    used = user.signals_used_this_month or 0
    if used >= max_signals:
        msg = (
            f"You've reached the {plan.title()} plan limit of {max_signals} signals this month. "
            f"Please upgrade for higher limits."
        )
        logger.info("Signal limit hit: %d/%d for user %s on plan %s",
                     used, max_signals, user_id, plan)
        return False, (jsonify({"status": "error", "error": msg}), 429)

    return True, None


def increment_signal_usage(user_id: str, amount: int = 1):
    """
    Increment the user's signal usage counter for the current month.
    Safe to call after successfully processing a webhook signal.
    """
    from app import db
    user = User.query.get(user_id)
    if not user:
        return
    user.signals_used_this_month = (user.signals_used_this_month or 0) + amount
    db.session.commit()
    logger.debug("Incremented signal usage for user %s by %d", user_id, amount)


def count_user_strategies(user_id: str) -> int:
    """Return the number of webhook strategies owned by this user."""
    from database.strategy_db import get_user_strategies
    return len(get_user_strategies(user_id))


def count_user_chartink_strategies(user_id: str) -> int:
    """Return the number of Chartink strategies owned by this user."""
    from database.chartink_db import get_user_strategies
    return len(get_user_strategies(user_id))


def count_user_python_strategies(user_id: str) -> int:
    """Return the number of Python strategy configs owned by this user."""
    from blueprints.python_strategy import STRATEGY_CONFIGS
    return sum(
        1 for cfg in STRATEGY_CONFIGS.values()
        if cfg.get("user_id") == user_id
    )


def count_user_workflows(_user_id: str) -> int:
    """Return total workflows (user-agnostic — FlowWorkflow has no user_id column)."""
    from database.flow_db import get_all_workflows
    return len(get_all_workflows())


# ── Core capacity check ──────────────────────────────────────────────────


def check_capacity_or_error(
    limit_key: str,
    current_count: int,
):
    """
    Check if the current user has capacity for a plan-limited resource.

    Args:
        limit_key:  Key into ``PLAN_LIMITS`` (e.g. ``"active_strategies"``).
        current_count:  How many of this resource the user already has.

    Returns:
        ``(True, None)`` if there is capacity.
        ``(False, (jsonify_response, status_code))`` if the limit is exceeded
        or the feature is disabled.
    """
    user_id = session.get("user")
    if not user_id:
        return False, (jsonify({"status": "error", "message": "Session expired"}), 401)

    user = User.query.get(user_id)
    if not user:
        return False, (jsonify({"status": "error", "message": "User not found"}), 404)

    plan = user.plan or "free"
    limits = PLAN_LIMITS.get(plan, PLAN_LIMITS["free"])
    max_items = limits.get(limit_key)

    # null = unlimited
    if max_items is None:
        return True, None

    # 0 = feature not available on this plan
    if max_items == 0:
        msg = (
            f"This feature is not available on the {plan.title()} plan. "
            f"Please upgrade to access it."
        )
        logger.info("Plan limit hit: %s (limit=0) for user %s on plan %s",
                     limit_key, user_id, plan)
        return False, (jsonify({"status": "error", "message": msg}), 403)

    # Numeric cap
    if current_count >= max_items:
        label = limit_key.replace("_", " ")
        msg = (
            f"You've reached the {plan.title()} plan limit of {max_items} {label}. "
            f"Please upgrade to add more."
        )
        logger.info("Plan limit hit: %s (%d/%d) for user %s on plan %s",
                     limit_key, current_count, max_items, user_id, plan)
        return False, (jsonify({"status": "error", "message": msg}), 403)

    return True, None


# ── Decorator form ───────────────────────────────────────────────────────


def check_plan_capacity(limit_key: str, count_fn):
    """
    Decorator: check plan capacity before the endpoint runs.

    Args:
        limit_key:  ``PLAN_LIMITS`` key.
        count_fn:   Callable that accepts ``(user_id: str)`` and returns
                    the current count of the resource.
    """
    def decorator(f):
        @wraps(f)
        def wrapper(*args, **kwargs):
            user_id = session.get("user")
            if not user_id:
                return jsonify({"status": "error", "message": "Session expired"}), 401

            try:
                current_count = count_fn(user_id)
            except Exception:
                logger.exception("Failed to count resources for limit %s", limit_key)
                return jsonify({"status": "error", "message": "Failed to check plan limits"}), 500

            ok, error_response = check_capacity_or_error(limit_key, current_count)
            if not ok:
                return error_response

            return f(*args, **kwargs)
        return wrapper
    return decorator
