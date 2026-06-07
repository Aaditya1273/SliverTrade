"""Gunicorn configuration for SilverTrade AI.

Auto-scales workers to (2 × CPU cores) + 1 for optimal throughput under
1 000+ concurrent users.  All parameters can be overridden via environment
variables so the Docker entrypoint stays clean.

References
----------
- Gunicorn settings: https://docs.gunicorn.org/en/stable/settings.html
- The (2 × CPU) + 1 rule: https://docs.gunicorn.org/en/stable/design.html
"""

import multiprocessing
import os

# ---------------------------------------------------------------------------
# Worker process count
# ---------------------------------------------------------------------------
# Default: (2 × CPU cores) + 1.  This is the standard gunicorn formula that
# balances CPU-bound and I/O-bound work.  Override via GUNICORN_WORKERS.
# For eventlet async workers, reduce to (CPU cores) to avoid eventlet
# overhead on CPU-heavy machines.
_cores = multiprocessing.cpu_count()
workers = int(os.getenv("GUNICORN_WORKERS", str(2 * _cores + 1)))

# ---------------------------------------------------------------------------
# Worker class
# ---------------------------------------------------------------------------
# eventlet is required because Flask-SocketIO uses monkey-patched async.
# Set GUNICORN_WORKER_CLASS=gevent or sync for non-WebSocket deployments.
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "eventlet")

# ---------------------------------------------------------------------------
# Listening socket
# ---------------------------------------------------------------------------
bind = os.getenv("GUNICORN_BIND", "0.0.0.0:5000")

# ---------------------------------------------------------------------------
# Timeouts
# ---------------------------------------------------------------------------
# Workers that fail to respond within *timeout* seconds are killed and
# restarted.  120s is generous for long-poll order execution and
# historical data endpoints.
timeout = int(os.getenv("GUNICORN_TIMEOUT", "120"))

# Seconds to wait for workers to finish in-progress requests on shutdown.
# 30s gives slow broker API calls a chance to complete.
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))

# Seconds to wait for the worker boot (e.g. DB init, cache warmup).
# If a worker takes longer than this gunicorn kills it and logs a
# CRITICAL message.
worker_timeout = int(os.getenv("GUNICORN_WORKER_TIMEOUT", "120"))

# ---------------------------------------------------------------------------
# Max requests — prevent memory leaks
# ---------------------------------------------------------------------------
# Each worker is restarted after handling this many requests.  This is the
# primary defence against gradual memory bloat (unclosed connections,
# cache growth, etc.) under sustained 1000+ concurrent load.
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "10000"))
# Add some jitter so workers don't all restart at exactly the same time.
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "1000"))

# ---------------------------------------------------------------------------
# Preload — save memory by sharing the app across workers
# ---------------------------------------------------------------------------
# Load the application code before forking workers.  This reduces per-worker
# memory by sharing read-only pages (Copy-on-Write).  Disable if the app
# has issues with preloading (e.g. connection pools created before fork).
preload_app = os.getenv("GUNICORN_PRELOAD", "true").lower() in ("true", "1")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
# Access logs are handled by the app's traffic_logger, so disable gunicorn's
# own access log to avoid double-logging.
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "/dev/null")
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "warning")

# ---------------------------------------------------------------------------
# Worker tmp dir — must be on a writable volume, not a read-only mount
# ---------------------------------------------------------------------------
worker_tmp_dir = os.getenv("GUNICORN_WORKER_TMP_DIR", os.path.join(os.sep, 'tmp', 'gunicorn_workers'))

# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------


def on_starting(server):
    """Log how many workers will be started."""
    server.log.info(
        "SilverTrade AI — starting %s workers (%d CPU cores, class=%s, preload=%s)",
        workers,
        _cores,
        worker_class,
        preload_app,
    )


def worker_abort(worker):
    """Log the reason a worker was killed (timeout, OOM, etc.)."""
    worker.log.warning("Worker %s aborted — likely timeout or OOM", worker.pid)


def post_worker_init(worker):
    """Worker initialisation hook — log worker PID for debugging."""
    worker.log.info("Worker %s initialised and ready", worker.pid)
