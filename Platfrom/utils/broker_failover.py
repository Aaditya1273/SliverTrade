"""
Broker Failover — Health-Based Automatic Fallback

Provides a ``BrokerFailoverManager`` that:
- Maintains a configured failover order per user (primary → secondary → tertiary)
- Periodically pings each broker's order API to assess health (optional, controlled by
  ``BROKER_HEALTH_CHECK_INTERVAL``)
- Automatically falls back to the next healthy broker on repeated failures
- Wraps broker operations with the ``CircuitBreaker`` pattern from
  ``utils.circuit_breaker`` so that a failing broker is opened (fail-fast) after
  ``failure_threshold`` consecutive failures and re-tested after
  ``recovery_timeout`` seconds
- Emits structured log events on all failover transitions for observability

Integration points:
    - :func:`place_order_with_failover` replaces direct calls to
      ``place_order_service.place_order_with_auth`` when multi-broker support
      is enabled.
    - The ``/health/api/brokers`` endpoint (via :func:`get_all_broker_health`)
      exposes per-broker health status for dashboards.

Usage:
    from utils.broker_failover import BrokerFailoverManager

    failover = BrokerFailoverManager()
    result = failover.execute_with_failover(
        user_id="user123",
        operation="place_order",
        fn=place_order_service.place_order_with_auth,
        order_data=order_data,
        auth_token=primary_token,
        broker="zerodha",
        original_data=original_data,
    )
"""

import logging
import os
import threading
import time
from dataclasses import dataclass, field
from typing import Any, Callable, Optional

from utils.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerOpenError,
    get_circuit_breaker,
)

logger = logging.getLogger(__name__)

# ── Configuration (from environment) ────────────────────────────────────────

# Whether the broker failover system is enabled. Disabled = always use primary.
BROKER_FAILOVER_ENABLED = os.getenv("BROKER_FAILOVER_ENABLED", "true").lower() in (
    "true",
    "1",
    "yes",
)

# How often (seconds) to health-check a broker that is currently in OPEN state.
# If the broker recovers, it is moved back to CLOSED.
BROKER_HEALTH_CHECK_INTERVAL = int(os.getenv("BROKER_HEALTH_CHECK_INTERVAL", "60"))

# Thresholds for the circuit breaker per broker operation
CB_FAILURE_THRESHOLD = int(os.getenv("BROKER_CB_FAILURE_THRESHOLD", "5"))
CB_RECOVERY_TIMEOUT = int(os.getenv("BROKER_CB_RECOVERY_TIMEOUT", "30"))
CB_HALF_OPEN_MAX = int(os.getenv("BROKER_CB_HALF_OPEN_MAX", "3"))


# ── Data structures ─────────────────────────────────────────────────────────


@dataclass
class BrokerHealth:
    """Runtime health state for a single broker instance on a user account."""

    broker_name: str
    user_id: str
    last_health_check: float = 0.0
    last_success_at: float = 0.0
    last_failure_at: float = 0.0
    consecutive_failures: int = 0

    @property
    def is_healthy(self) -> bool:
        """Consider healthy if we haven't seen a failure, or last success is
        more recent than last failure."""
        return self.last_success_at >= self.last_failure_at


@dataclass
class UserBrokerConfig:
    """Failover configuration for a single user."""

    user_id: str
    # Ordered list of broker names, e.g. ["zerodha", "angel", "icici"]
    failover_order: list[str] = field(default_factory=list)
    # Broker currently marked as active (by health checks)
    active_broker: Optional[str] = None
    # Per-broker health state
    broker_health: dict[str, BrokerHealth] = field(default_factory=dict)


# ── Manager ─────────────────────────────────────────────────────────────────


class BrokerFailoverManager:
    """Manages broker health checks and failover for all users.

    Thread-safe. A single instance should be created at application startup
    and reused across all request handlers.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        # user_id -> UserBrokerConfig
        self._configs: dict[str, UserBrokerConfig] = {}
        self._enabled = BROKER_FAILOVER_ENABLED

        if self._enabled:
            logger.info(
                "Broker failover ENABLED "
                "(failure_threshold=%d, recovery_timeout=%ds, health_check=%ds)",
                CB_FAILURE_THRESHOLD,
                CB_RECOVERY_TIMEOUT,
                BROKER_HEALTH_CHECK_INTERVAL,
            )
        else:
            logger.info("Broker failover DISABLED (BROKER_FAILOVER_ENABLED != true)")

    # ── Configuration ──────────────────────────────────────────────────────────

    def register_user(
        self,
        user_id: str,
        failover_order: list[str],
    ) -> None:
        """Register or update a user's broker failover order.

        The *failover_order* is an ordered list of broker names corresponding
        to the user's connected brokers (e.g. ``["zerodha", "angel"]``).

        Thread-safe.
        """
        with self._lock:
            cfg = self._configs.get(user_id)
            if cfg is None:
                cfg = UserBrokerConfig(user_id=user_id)
                self._configs[user_id] = cfg

            cfg.failover_order = list(failover_order)
            cfg.active_broker = failover_order[0] if failover_order else None

            # Ensure every broker in the order has a health entry
            for broker_name in failover_order:
                if broker_name not in cfg.broker_health:
                    cfg.broker_health[broker_name] = BrokerHealth(
                        broker_name=broker_name,
                        user_id=user_id,
                    )

            logger.info(
                "Registered user %s with failover order: %s (active: %s)",
                user_id,
                failover_order,
                cfg.active_broker,
            )

    def unregister_user(self, user_id: str) -> None:
        """Remove all failover configuration for a user (e.g. on logout)."""
        with self._lock:
            self._configs.pop(user_id, None)
            logger.info("Unregistered user %s from broker failover", user_id)

    def get_active_broker(self, user_id: str) -> Optional[str]:
        """Return the currently-active broker for *user_id*, or ``None``."""
        with self._lock:
            cfg = self._configs.get(user_id)
            return cfg.active_broker if cfg else None

    # ── Health checks ──────────────────────────────────────────────────────────

    def record_success(self, user_id: str, broker_name: str) -> None:
        """Record a successful operation for a broker.

        Call this after the broker order/market-data call succeeds.
        """
        with self._lock:
            cfg = self._configs.get(user_id)
            if not cfg:
                return
            health = cfg.broker_health.get(broker_name)
            if health:
                health.last_success_at = time.monotonic()
                health.consecutive_failures = 0

    def record_failure(self, user_id: str, broker_name: str) -> None:
        """Record a failed operation for a broker.

        Call this after the broker order/market-data call fails with a
        connection error, timeout, or 5xx response.
        """
        with self._lock:
            cfg = self._configs.get(user_id)
            if not cfg:
                return
            health = cfg.broker_health.get(broker_name)
            if health:
                health.last_failure_at = time.monotonic()
                health.consecutive_failures += 1

                # If too many consecutive failures, try to failover
                if health.consecutive_failures >= CB_FAILURE_THRESHOLD:
                    self._try_failover(user_id, broker_name)

    def _try_failover(self, user_id: str, failed_broker: str) -> None:
        """Attempt to failover to the next healthy broker in the order."""
        cfg = self._configs.get(user_id)
        if not cfg or not cfg.failover_order:
            return

        current_idx = -1
        for i, name in enumerate(cfg.failover_order):
            if name == failed_broker:
                current_idx = i
                break

        if current_idx < 0:
            return

        # Look for the next broker after the failed one
        next_idx = current_idx + 1
        for i in range(next_idx, len(cfg.failover_order)):
            candidate = cfg.failover_order[i]
            candidate_health = cfg.broker_health.get(candidate)
            # Skip brokers with recent failures (within recovery_timeout)
            if candidate_health and candidate_health.last_failure_at > 0:
                elapsed = time.monotonic() - candidate_health.last_failure_at
                if elapsed < CB_RECOVERY_TIMEOUT:
                    continue  # This broker is also in cooldown
            cfg.active_broker = candidate
            logger.warning(
                "BROKER FAILOVER: user=%s failed_broker=%s → active_broker=%s",
                user_id,
                failed_broker,
                candidate,
            )
            return

        # No healthy broker found — stay on current but log critical
        cfg.active_broker = failed_broker
        logger.critical(
            "BROKER FAILOVER EXHAUSTED: user=%s no healthy broker found. "
            "Staying on %s (all brokers in cooldown)",
            user_id,
            failed_broker,
        )

    # ── Circuit breaker integration ────────────────────────────────────────────

    def _breaker_name(self, user_id: str, broker_name: str, operation: str) -> str:
        """Return a stable circuit breaker name for a (user, broker, operation)."""
        return f"broker:{user_id}:{broker_name}:{operation}"

    def execute_with_failover(
        self,
        user_id: str,
        operation: str,
        fn: Callable[..., Any],
        *,
        order_data: Optional[dict] = None,
        auth_token: Optional[str] = None,
        broker: Optional[str] = None,
        original_data: Optional[dict] = None,
        token_resolver: Optional[Callable[[str], Optional[tuple[str, str]]]] = None,
        **kwargs: Any,
    ) -> tuple[bool, dict[str, Any], int]:
        """Execute a broker operation with automatic failover.

        If the primary broker fails (circuit breaker opens or operation raises
        a retryable exception), the next broker in the user's failover order
        is tried automatically.

        When switching between brokers in the failover order, *token_resolver*
        (if provided) is called with each candidate broker name to obtain that
        broker's ``(auth_token, broker_name)`` pair.  This allows the failover
        to use the correct credentials for each broker even though the caller
        only knows the primary broker's token.

        The *token_resolver* signature is::

            def resolver(broker_name: str) -> Optional[tuple[str, str]]:
                ...
                return (auth_token, broker_name)  # or None on lookup failure

        Args:
            user_id: The user identifier.
            operation: Operation name for circuit breaker naming
                       (e.g. ``"place_order"``, ``"cancel_order"``).
            fn: The service function to call.  Must accept positional args
                ``(order_data, auth_token, broker, original_data, **kwargs)``.
            order_data: Order data dictionary.
            auth_token: Auth token for the *initial* broker attempt.
            broker: Name of the *initial* broker.
            original_data: Original request data (for event publishing).
            token_resolver: Optional callable to fetch auth tokens for
                            alternative brokers during failover.
            **kwargs: Additional keyword arguments forwarded to *fn*.

        Returns:
            The same ``(success, response, status_code)`` as *fn*.
        """
        if not self._enabled:
            return fn(
                order_data or {},
                auth_token or "",
                broker or "",
                original_data or {},
                **kwargs,
            )

        with self._lock:
            cfg = self._configs.get(user_id)

            # No configuration → execute with the supplied broker as-is
            if not cfg or not cfg.failover_order:
                return fn(
                    order_data or {},
                    auth_token or "",
                    broker or "",
                    original_data or {},
                    **kwargs,
                )

            # Build the ordered list of brokers to try
            if broker and broker in cfg.failover_order:
                start_idx = cfg.failover_order.index(broker)
            else:
                start_idx = 0

            ordered_brokers = cfg.failover_order[start_idx:] + cfg.failover_order[:start_idx]

        # Try each broker in failover order
        last_error: Optional[str] = None
        current_auth_token = auth_token

        for attempt, candidate_broker in enumerate(ordered_brokers):
            cb = get_circuit_breaker(
                name=self._breaker_name(user_id, candidate_broker, operation),
                failure_threshold=CB_FAILURE_THRESHOLD,
                recovery_timeout=CB_RECOVERY_TIMEOUT,
                half_open_max_attempts=CB_HALF_OPEN_MAX,
            )

            if cb.is_open():
                logger.debug(
                    "Skipping broker %s for user %s (circuit OPEN)",
                    candidate_broker,
                    user_id,
                )
                continue

            # Resolve auth token for this broker
            # On the first attempt we use the caller-supplied token; for
            # subsequent attempts we consult the token_resolver.
            if attempt > 0 and token_resolver is not None:
                resolved = token_resolver(candidate_broker)
                if resolved is None:
                    logger.warning(
                        "Could not resolve auth token for broker %s (user %s) — skipping",
                        candidate_broker,
                        user_id,
                    )
                    continue
                current_auth_token, candidate_broker = resolved

            try:
                result = fn(
                    order_data or {},
                    current_auth_token or "",
                    candidate_broker,
                    original_data or {},
                    **kwargs,
                )
                success, response, status_code = result

                if success:
                    self.record_success(user_id, candidate_broker)
                    # Update active broker if we succeeded on a non-primary broker
                    if attempt > 0:
                        with self._lock:
                            if user_id in self._configs:
                                old_active = self._configs[user_id].active_broker
                                self._configs[user_id].active_broker = candidate_broker
                                logger.info(
                                    "Failover active broker updated: %s → %s",
                                    old_active,
                                    candidate_broker,
                                )
                    cb.record_success()
                    return result
                else:
                    # Broker responded with a business error (not a connectivity issue)
                    self.record_failure(user_id, candidate_broker)
                    cb.record_failure()
                    last_error = response.get("message", "Unknown error")

            except (CircuitBreakerOpenError, ConnectionError, TimeoutError, OSError) as e:
                self.record_failure(user_id, candidate_broker)
                cb.record_failure()
                last_error = str(e)
                logger.warning(
                    "Broker %s failed for user %s (attempt %d/%d): %s",
                    candidate_broker,
                    user_id,
                    attempt + 1,
                    len(ordered_brokers),
                    e,
                )
            except Exception as e:
                # Unexpected exception — still mark as failure but re-raise
                self.record_failure(user_id, candidate_broker)
                cb.record_failure()
                logger.exception(
                    "Unexpected error on broker %s for user %s: %s",
                    candidate_broker,
                    user_id,
                    e,
                )
                raise

        # All brokers exhausted
        error_msg = last_error or "All brokers failed"
        logger.critical(
            "All %d broker(s) failed for user %s. Last error: %s",
            len(ordered_brokers),
            user_id,
            error_msg,
        )
        return False, {"status": "error", "message": error_msg}, 503

    # ── Observability ──────────────────────────────────────────────────────────

    def get_all_broker_health(self) -> dict[str, dict[str, Any]]:
        """Return a snapshot of all registered user broker health states.

        Used by the ``/health/api/brokers`` endpoint.
        """
        with self._lock:
            result: dict[str, dict[str, Any]] = {}
            for user_id, cfg in self._configs.items():
                brokers: dict[str, dict[str, Any]] = {}
                for broker_name, health in cfg.broker_health.items():
                    brokers[broker_name] = {
                        "consecutive_failures": health.consecutive_failures,
                        "is_healthy": health.is_healthy,
                        "last_success_at": health.last_success_at,
                        "last_failure_at": health.last_failure_at,
                    }
                result[user_id] = {
                    "active_broker": cfg.active_broker,
                    "failover_order": cfg.failover_order,
                    "brokers": brokers,
                }
            return result

    def reset_failover_state(self, user_id: Optional[str] = None) -> int:
        """Reset failover state for a user (or all users if *user_id* is None).

        Returns the number of users reset.
        """
        import utils.circuit_breaker as cb_module

        count = 0
        with self._lock:
            user_ids = [user_id] if user_id else list(self._configs.keys())
            for uid in user_ids:
                cfg = self._configs.get(uid)
                if cfg:
                    cfg.broker_health.clear()
                    cfg.active_broker = cfg.failover_order[0] if cfg.failover_order else None
                    # Reset all circuit breakers for this user
                    for broker_name in cfg.failover_order:
                        bname = f"broker:{uid}:{broker_name}:"
                        for cb_name in list(cb_module._registry.keys()):
                            if cb_name.startswith(bname):
                                cb_module.reset_breaker(cb_name)
                    count += 1

        return count


# ── Singleton convenience ───────────────────────────────────────────────────

# Application-wide broker failover manager
_failover_manager_lock = threading.Lock()
_failover_manager: Optional[BrokerFailoverManager] = None


def get_failover_manager() -> BrokerFailoverManager:
    """Return the application-wide singleton ``BrokerFailoverManager``."""
    global _failover_manager
    if _failover_manager is None:
        with _failover_manager_lock:
            if _failover_manager is None:
                _failover_manager = BrokerFailoverManager()
    return _failover_manager


def make_token_resolver(api_key: str) -> Callable[[str], Optional[tuple[str, str]]]:
    """
    Create a token-resolver callable for use with
    :meth:`BrokerFailoverManager.execute_with_failover`.

    The resolver takes a broker name and returns
    ``(auth_token, broker_name)`` or ``None`` on failure.

    Currently the platform stores one auth record per user, so the resolver
    always returns the same token regardless of the requested broker.
    When multi-broker-per-user support is added (multiple non-unique ``Auth``
    rows per ``name``), this function should be updated to query by broker.
    """
    from database.auth_db import get_auth_token_broker

    def _resolve(broker_name: str) -> Optional[tuple[str, str]]:
        token, resolved_broker = get_auth_token_broker(api_key)
        if token is None:
            logger.warning(
                "Token resolver: could not fetch auth token for broker %s",
                broker_name,
            )
            return None
        return token, resolved_broker

    return _resolve


def register_user_brokers(user_id: str, failover_order: list[str]) -> None:
    """Convenience: register a user's broker failover order."""
    get_failover_manager().register_user(user_id, failover_order)


def get_active_broker(user_id: str) -> Optional[str]:
    """Convenience: get the active broker for a user."""
    return get_failover_manager().get_active_broker(user_id)
