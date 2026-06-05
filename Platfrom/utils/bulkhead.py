"""
Bulkhead Isolation — Thread Pool Separation for Resilient Execution

Prevents a slow or failing subsystem from exhausting all threads in the
application by dedicating independent thread pools to different operation
categories.  Loosely modelled after the bulkhead pattern from resilience4j.

Operation categories (each gets its own bounded thread pool):

+------------------------+-----------------------------------------------+
| Category               | Typical operations                             |
+------------------------+-----------------------------------------------+
| ``ORDERS``             | Place, modify, cancel, close positions         |
| ``MARKET_DATA``        | Fetch quotes, depth, LTP, option chains        |
| ``DATABASE_QUERY``     | Report/historical queries, analytics, exports  |
| ``ADMIN``              | Login, registration, settings, config updates  |
| ``TELEGRAM``           | Telegram bot message handling                  |
| ``WEBSOCKET``          | WebSocket proxy subscription changes           |
+------------------------+-----------------------------------------------+

Usage:

    from utils.bulkhead import get_executor, BulkheadCategory, submit_task

    # Fire-and-forget (best effort)
    submit_task(BulkheadCategory.ORDERS, place_order, order_data=...)

    # Blocking call with timeout
    future = get_executor(BulkheadCategory.DATABASE_QUERY).submit(
        expensive_query, symbol="RELIANCE"
    )
    result = future.result(timeout=30.0)

Configuration (environment variables):

    ``BULKHEAD_ORDERS_POOL``         — Max threads for order operations (default: 5)
    ``BULKHEAD_MARKET_DATA_POOL``    — Max threads for market data (default: 10)
    ``BULKHEAD_DATABASE_POOL``       — Max threads for DB queries (default: 5)
    ``BULKHEAD_ADMIN_POOL``          — Max threads for admin/telegram (default: 3)
    ``BULKHEAD_QUEUE_SIZE``          — Max queue depth per pool (default: 100)
"""

import logging
import os
import threading
import time
from concurrent.futures import Future, ThreadPoolExecutor
from dataclasses import dataclass
from enum import Enum
from queue import Queue
from typing import Any, Callable, Optional

logger = logging.getLogger(__name__)


class BulkheadCategory(Enum):
    """Operation categories, each mapped to a dedicated thread pool."""

    ORDERS = "orders"
    MARKET_DATA = "market_data"
    DATABASE_QUERY = "database_query"
    ADMIN = "admin"
    TELEGRAM = "telegram"
    WEBSOCKET = "websocket"


# ── Configuration from environment ────────────────────────────────────────────

DEFAULT_POOL_SIZES: dict[BulkheadCategory, int] = {
    BulkheadCategory.ORDERS: 5,
    BulkheadCategory.MARKET_DATA: 10,
    BulkheadCategory.DATABASE_QUERY: 5,
    BulkheadCategory.ADMIN: 3,
    BulkheadCategory.TELEGRAM: 3,
    BulkheadCategory.WEBSOCKET: 3,
}

QUEUE_SIZE = int(os.getenv("BULKHEAD_QUEUE_SIZE", "100"))

# Map env var names → categories
_ENV_OVERRIDES: dict[str, BulkheadCategory] = {
    "BULKHEAD_ORDERS_POOL": BulkheadCategory.ORDERS,
    "BULKHEAD_MARKET_DATA_POOL": BulkheadCategory.MARKET_DATA,
    "BULKHEAD_DATABASE_POOL": BulkheadCategory.DATABASE_QUERY,
    "BULKHEAD_ADMIN_POOL": BulkheadCategory.ADMIN,
}


def _resolve_pool_size(category: BulkheadCategory) -> int:
    """Read pool size from env var or return default."""
    env_key = f"BULKHEAD_{category.name}_POOL"
    try:
        return int(os.environ.get(env_key, str(DEFAULT_POOL_SIZES.get(category, 5))))
    except (ValueError, TypeError):
        return DEFAULT_POOL_SIZES.get(category, 5)


# ── Dead-letter queue ─────────────────────────────────────────────────────────

_dead_letter_queue: Queue = Queue()


@dataclass
class DeadLetter:
    """Record of a task that was rejected or failed irrevocably."""
    category: BulkheadCategory
    task_name: str
    error: str
    submitted_at: float
    payload: Optional[dict] = None


def submit_to_dead_letter(category: BulkheadCategory, task_name: str, error: str) -> None:
    """Push a failed task onto the dead-letter queue for later inspection.

    The dead-letter queue is bounded at 1000 entries.  Oldest entries are
    discarded when full.
    """
    entry = DeadLetter(
        category=category,
        task_name=task_name,
        error=error,
        submitted_at=time.monotonic(),
    )
    if _dead_letter_queue.qsize() >= 1000:
        try:
            _dead_letter_queue.get_nowait()  # discard oldest
        except Exception:
            pass
    _dead_letter_queue.put_nowait(entry)


def drain_dead_letter_queue() -> list[DeadLetter]:
    """Drain and return all entries from the dead-letter queue.

    Consumed entries are removed permanently.  Use :func:`peek_dead_letter_queue`
    to inspect without consuming.
    """
    entries: list[DeadLetter] = []
    while not _dead_letter_queue.empty():
        try:
            entries.append(_dead_letter_queue.get_nowait())
        except Exception:
            break
    return entries


def peek_dead_letter_queue(limit: int = 50) -> list[DeadLetter]:
    """Return up to *limit* dead-letter entries without consuming them.

    Non-destructive inspection for monitoring endpoints.
    """
    try:
        # Access the underlying deque (thread-safe read via list copy)
        queue_data = list(_dead_letter_queue.queue)
        return queue_data[:limit]
    except Exception:
        return []


# ── Metrics (for Prometheus / monitoring) ─────────────────────────────────────

class BulkheadMetrics:
    """Gathers per-pool utilisation metrics for observability.

    Thread-safe. A single instance is shared across all pools via
    ``_task_monitor``.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._active: dict[BulkheadCategory, int] = {}
        self._completed: dict[BulkheadCategory, int] = {}
        self._rejected: dict[BulkheadCategory, int] = {}

    def record_submit(self, category: BulkheadCategory) -> None:
        with self._lock:
            self._active[category] = self._active.get(category, 0) + 1

    def record_complete(self, category: BulkheadCategory) -> None:
        with self._lock:
            self._active[category] = max(0, self._active.get(category, 0) - 1)
            self._completed[category] = self._completed.get(category, 0) + 1

    def record_rejected(self, category: BulkheadCategory) -> None:
        with self._lock:
            self._rejected[category] = self._rejected.get(category, 0) + 1

    def snapshot(self) -> dict[str, int]:
        with self._lock:
            result: dict[str, int] = {}
            for cat in BulkheadCategory:
                result[f"{cat.value}_active"] = self._active.get(cat, 0)
                result[f"{cat.value}_completed"] = self._completed.get(cat, 0)
                result[f"{cat.value}_rejected"] = self._rejected.get(cat, 0)
            result["dead_letter_queue_size"] = _dead_letter_queue.qsize()
            return result


_metrics = BulkheadMetrics()


def get_bulkhead_metrics() -> dict[str, int]:
    """Return a snapshot of all bulkhead metrics.

    Called by the ``/health/api/bulkheads`` endpoint.
    """
    return _metrics.snapshot()


# ── Pool registry ─────────────────────────────────────────────────────────────

_pools: dict[BulkheadCategory, ThreadPoolExecutor] = {}
_pool_lock = threading.Lock()


def get_executor(category: BulkheadCategory) -> ThreadPoolExecutor:
    """Return the thread pool executor for a given *category*.

    Pools are created lazily on first access and cached thereafter.
    """
    with _pool_lock:
        executor = _pools.get(category)
        if executor is None:
            max_workers = _resolve_pool_size(category)
            executor = _ThreadPoolWithMetrics(
                max_workers=max_workers,
                category=category,
                thread_name_prefix=f"bulkhead_{category.value}",
            )
            _pools[category] = executor
            logger.info(
                "Bulkhead pool '%s' created (max_workers=%d, queue_size=%d)",
                category.value,
                max_workers,
                QUEUE_SIZE,
            )
        return executor


# ── Custom executor with metrics and dead-letter tracking ─────────────────────

class _ThreadPoolWithMetrics(ThreadPoolExecutor):
    """A ``ThreadPoolExecutor`` subclass that records metrics and rejects tasks
    when the pool's work queue is full.
    """

    def __init__(
        self,
        max_workers: int,
        category: BulkheadCategory,
        thread_name_prefix: str = "",
    ) -> None:
        self._bulkhead_category = category

        super().__init__(
            max_workers=max_workers,
            thread_name_prefix=thread_name_prefix or f"bulkhead_{category.value}",
        )
        # NOTE: The default work queue is unbounded (queue.SimpleQueue in Python 3.7+).
        # We apply backpressure at the submit() level by checking qsize() so that
        # a full queue raises RuntimeError instead of blocking the caller.

    def submit(self, fn: Callable[..., Any], *args: Any, **kwargs: Any) -> Future:  # type: ignore[override]
        """Submit a task, or raise ``RuntimeError`` if the pool queue is full.

        Uses ``self._work_queue.qsize()`` to check queue depth before submitting.
        ``qsize()`` is approximate on most platforms — an exceptionally fast task
        may slip in while we check — but serves as a practical throttle for the
        bulkhead pattern.
        """
        # Check queue depth before submitting (approximate — see docstring)
        if self._work_queue.qsize() >= QUEUE_SIZE:
            _metrics.record_rejected(self._bulkhead_category)
            submit_to_dead_letter(
                self._bulkhead_category,
                getattr(fn, "__name__", "unnamed"),
                f"Bulkhead queue full ({QUEUE_SIZE})",
            )
            raise RuntimeError(
                f"Bulkhead '{self._bulkhead_category.value}' queue full ({QUEUE_SIZE}). "
                f"Task '{getattr(fn, '__name__', 'unnamed')}' rejected."
            )

        future = super().submit(fn, *args, **kwargs)
        _metrics.record_submit(self._bulkhead_category)

        # Track completion and dead-letter failures via done callback
        original_fn = fn

        def _on_done(_f: Future) -> None:
            _metrics.record_complete(self._bulkhead_category)
            exc = _f.exception()
            if exc is not None:
                submit_to_dead_letter(
                    self._bulkhead_category,
                    getattr(original_fn, "__name__", "unnamed"),
                    str(exc),
                )

        future.add_done_callback(_on_done)
        return future


# ── Convenience helpers ───────────────────────────────────────────────────────


def submit_task(
    category: BulkheadCategory,
    fn: Callable[..., Any],
    *args: Any,
    **kwargs: Any,
) -> Future:
    """Submit *fn* to the appropriate bulkhead pool.

    Returns a ``Future`` immediately (non-blocking).
    Raises ``RuntimeError`` if the pool queue is full.
    """
    executor = get_executor(category)
    return executor.submit(fn, *args, **kwargs)


def execute_in_bulkhead(
    category: BulkheadCategory,
    fn: Callable[..., Any],
    *args: Any,
    timeout: float = 30.0,
    **kwargs: Any,
) -> Any:
    """Execute *fn* in the appropriate bulkhead pool and wait for the result.

    Args:
        category: Which thread pool to use.
        fn: The callable to execute.
        timeout: Maximum seconds to wait for completion.
        *args, **kwargs: Passed to *fn*.

    Returns:
        The return value of *fn*.

    Raises:
        RuntimeError: If the pool queue is full.
        concurrent.futures.TimeoutError: If *fn* does not complete within *timeout* seconds.
        Exception: Any exception raised by *fn*.
    """
    future = submit_task(category, fn, *args, **kwargs)
    return future.result(timeout=timeout)


# ── Startup / shutdown ────────────────────────────────────────────────────────


def shutdown_all_pools(timeout: float = 30.0) -> None:
    """Gracefully shut down all bulkhead thread pools.

    Called during application shutdown.  Waits up to *timeout* seconds for
    in-flight tasks to complete.
    """
    with _pool_lock:
        for category, executor in list(_pools.items()):
            try:
                executor.shutdown(wait=True, timeout=timeout)
                logger.info("Bulkhead pool '%s' shut down", category.value)
            except Exception as e:
                logger.warning("Error shutting down pool '%s': %s", category.value, e)
        _pools.clear()
