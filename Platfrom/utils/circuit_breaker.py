"""
Circuit Breaker Pattern

Implements the circuit breaker pattern to prevent cascading failures when
downstream services (broker WebSockets, databases, etc.) are unhealthy.

States:
    CLOSED  — Normal operation. Requests pass through to the wrapped function.
    OPEN    — Circuit is tripped. Requests fail fast with CircuitBreakerOpenError.
              After recovery_timeout seconds, transitions to HALF_OPEN.
    HALF_OPEN — Probation. A limited number of requests are allowed through to
                test if the downstream service has recovered.

Configuration:
    failure_threshold (int)    — Consecutive failures to trip OPEN (default 5).
    recovery_timeout (float)   — Seconds before CLOSED→HALF_OPEN transition (default 30).
    half_open_max_attempts (int) — Successful attempts in HALF_OPEN to close (default 3).

Usage:
    # Synchronous
    cb = CircuitBreaker("my_service")
    try:
        result = cb.call(my_function, arg1, arg2)
    except CircuitBreakerOpenError:
        # handle degraded mode

    # Asynchronous
    result = await cb.call_async(my_async_function, arg1, arg2)

    # Manual (when you want explicit control)
    cb = CircuitBreaker("my_service")
    if not cb.is_open():
        try:
            result = risky_operation()
            cb.record_success()
        except Exception:
            cb.record_failure()
            raise
"""

import asyncio
import logging
import threading
import time
from enum import Enum
from functools import wraps
from typing import (
    Any,
    Callable,
    Generic,
    Optional,
    TypeVar,
)

logger = logging.getLogger(__name__)


class CircuitBreakerState(Enum):
    CLOSED = "CLOSED"
    OPEN = "OPEN"
    HALF_OPEN = "HALF_OPEN"


class CircuitBreakerOpenError(Exception):
    """Raised when a request is rejected because the circuit is OPEN."""

    def __init__(
        self,
        name: str,
        state: CircuitBreakerState,
        retry_after: float | None = None,
    ):
        self.circuit_name = name
        self.circuit_state = state
        self.retry_after = retry_after
        msg = (
            f"Circuit '{name}' is {state.value}"
            + (f" — retry after {retry_after:.0f}s" if retry_after else "")
        )
        super().__init__(msg)


T = TypeVar("T")


class CircuitBreaker(Generic[T]):
    """Thread-safe circuit breaker using threading.Lock for all operations.

    Uses threading.Lock exclusively (not asyncio.Lock) because all critical
    sections are fast scalar reads/writes with no await yield points. This
    avoids fragility around event loop detection at init time and allows
    the breaker to be used from both sync and async contexts interchangeably.
    """

    def __init__(
        self,
        name: str,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_attempts: int = 3,
    ) -> None:
        self.name = name
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.half_open_max_attempts = half_open_max_attempts

        self._state = CircuitBreakerState.CLOSED
        self._failure_count = 0
        self._success_count = 0
        self._last_failure_time = 0.0
        self._last_state_change = 0.0
        self._total_failures = 0
        self._total_successes = 0
        self._lock = threading.Lock()

    # ── Public API ──────────────────────────────────────────────────────────

    @property
    def state(self) -> CircuitBreakerState:
        return self._state

    @property
    def failure_count(self) -> int:
        return self._failure_count

    @property
    def total_failures(self) -> int:
        return self._total_failures

    @property
    def total_successes(self) -> int:
        return self._total_successes

    def reset(self) -> None:
        """Force the circuit back to CLOSED and clear counters."""
        self._set_state(CircuitBreakerState.CLOSED)
        self._failure_count = 0
        self._success_count = 0
        logger.info("Circuit '%s' force-reset to CLOSED", self.name)

    # ── Synchronous call ────────────────────────────────────────────────────

    def call(self, fn: Callable[..., T], *args: Any, **kwargs: Any) -> T:
        """Execute *fn* under circuit breaker protection (synchronous)."""
        if self._try_acquire():
            try:
                result = fn(*args, **kwargs)
                self.record_success()
                return result
            except CircuitBreakerOpenError:
                raise
            except Exception as exc:
                self.record_failure()
                raise
        raise CircuitBreakerOpenError(
            self.name, self._state, self._remaining_seconds()
        )

    # ── Asynchronous call ───────────────────────────────────────────────────

    async def call_async(
        self, fn: Callable[..., Any], *args: Any, **kwargs: Any
    ) -> Any:
        """Execute *fn* under circuit breaker protection (asynchronous / awaitable)."""
        if self._try_acquire():
            try:
                result = await fn(*args, **kwargs) if asyncio.iscoroutinefunction(fn) else fn(*args, **kwargs)
                self.record_success()
                return result
            except CircuitBreakerOpenError:
                raise
            except Exception as exc:
                self.record_failure()
                raise
        raise CircuitBreakerOpenError(
            self.name, self._state, self._remaining_seconds()
        )

    # ── Manual success / failure recording ──────────────────────────────────

    def record_success(self) -> None:
        with self._lock:
            self._total_successes += 1

            if self._state == CircuitBreakerState.HALF_OPEN:
                self._success_count += 1
                if self._success_count >= self.half_open_max_attempts:
                    logger.info(
                        "Circuit '%s' closed after %d consecutive successes",
                        self.name,
                        self._success_count,
                    )
                    self._set_state(CircuitBreakerState.CLOSED)
                    self._failure_count = 0
                    self._success_count = 0
            elif self._state == CircuitBreakerState.CLOSED:
                self._failure_count = 0  # Reset failure count on success

    def record_failure(self) -> None:
        with self._lock:
            self._total_failures += 1
            self._last_failure_time = time.monotonic()

            if self._state == CircuitBreakerState.HALF_OPEN:
                # A single failure in HALF_OPEN trips back to OPEN immediately
                logger.warning(
                    "Circuit '%s' re-opened during half-open probation",
                    self.name,
                )
                self._set_state(CircuitBreakerState.OPEN)
                self._success_count = 0
            elif self._state == CircuitBreakerState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self.failure_threshold:
                    logger.warning(
                        "Circuit '%s' opened after %d consecutive failures",
                        self.name,
                        self._failure_count,
                    )
                    self._set_state(CircuitBreakerState.OPEN)
                    self._success_count = 0

    # ── Query helpers ───────────────────────────────────────────────────────

    def is_open(self) -> bool:
        """
        Check whether the circuit is currently OPEN (fail-fast).

        If the circuit is OPEN and the recovery timeout has elapsed, this
        automatically transitions to HALF_OPEN so callers that poll this
        method (like reconnect loops) can resume naturally.
        """
        with self._lock:
            if self._state == CircuitBreakerState.OPEN:
                if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                    logger.info(
                        "Circuit '%s' OPEN→HALF_OPEN (auto via is_open check)",
                        self.name,
                    )
                    self._set_state(CircuitBreakerState.HALF_OPEN)
                    self._success_count = 0
                    return False
                return True
            return False

    def stats(self) -> dict[str, Any]:
        """Return a snapshot of breaker metrics for monitoring."""
        return {
            "name": self.name,
            "state": self._state.value,
            "failure_count": self._failure_count,
            "success_count": self._success_count,
            "failure_threshold": self.failure_threshold,
            "recovery_timeout": self.recovery_timeout,
            "half_open_max_attempts": self.half_open_max_attempts,
            "last_failure_time": self._last_failure_time,
            "total_failures": self._total_failures,
            "total_successes": self._total_successes,
        }

    # ── Internal helpers ────────────────────────────────────────────────────

    def _try_acquire(self) -> bool:
        """Check whether the request should be allowed to proceed."""
        with self._lock:
            if self._state == CircuitBreakerState.CLOSED:
                return True

            if self._state == CircuitBreakerState.HALF_OPEN:
                return True  # Allow limited requests through

            # OPEN — check if recovery_timeout has elapsed
            if time.monotonic() - self._last_failure_time >= self.recovery_timeout:
                logger.info(
                    "Circuit '%s' transitioning OPEN → HALF_OPEN",
                    self.name,
                )
                self._set_state(CircuitBreakerState.HALF_OPEN)
                self._success_count = 0
                return True

            return False

    def _remaining_seconds(self) -> float | None:
        """Seconds until the circuit transitions from OPEN to HALF_OPEN."""
        if self._state != CircuitBreakerState.OPEN:
            return None
        elapsed = time.monotonic() - self._last_failure_time
        return max(0.0, self.recovery_timeout - elapsed)

    def _set_state(self, new_state: CircuitBreakerState) -> None:
        if new_state != self._state:
            logger.info(
                "Circuit '%s' state change: %s → %s",
                self.name,
                self._state.value,
                new_state.value,
            )
        self._state = new_state
        self._last_state_change = time.monotonic()


# ── Convenience: decorator factory ────────────────────────────────────────


def circuit_breaker(
    name: str = None,
    failure_threshold: int = 5,
    recovery_timeout: float = 30.0,
    half_open_max_attempts: int = 3,
):
    """Decorator that wraps a function with a named CircuitBreaker.

    The breaker instance is stored as ``func.__circuit_breaker__`` so it can
    be inspected or reset at runtime.

    Usage::

        @circuit_breaker("broker_connect", failure_threshold=3, recovery_timeout=15)
        def connect_to_broker():
            ...
    """
    cb = CircuitBreaker(
        name=name or "unnamed",
        failure_threshold=failure_threshold,
        recovery_timeout=recovery_timeout,
        half_open_max_attempts=half_open_max_attempts,
    )

    def decorator(fn):
        fn.__circuit_breaker__ = cb

        @wraps(fn)
        def sync_wrapper(*args, **kwargs):
            return cb.call(fn, *args, **kwargs)

        @wraps(fn)
        async def async_wrapper(*args, **kwargs):
            return await cb.call_async(fn, *args, **kwargs)

        wrapper = async_wrapper if asyncio.iscoroutinefunction(fn) else sync_wrapper
        return wrapper

    return decorator
