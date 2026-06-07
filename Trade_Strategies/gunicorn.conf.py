"""
Gunicorn configuration for SilverTrade AI — Trade Strategies.

Auto-scales workers to (2 × CPU cores) + 1 for optimal throughput.
All parameters can be overridden via environment variables so operators
can tune without editing files.

Key differences from the Platform API config:
- Uses sync workers (no SocketIO needed — this service is request/response)
- Higher default timeout (600s) for model training endpoints
- Preload enabled for memory efficiency

References
----------
- Gunicorn settings: https://docs.gunicorn.org/en/stable/settings.html
- Worker count formula: https://docs.gunicorn.org/en/stable/design.html
"""

import multiprocessing
import os

# ---------------------------------------------------------------------------
# Worker process count
# ---------------------------------------------------------------------------
# Default: (2 × CPU cores) + 1 — the standard gunicorn formula.
# Override via GUNICORN_WORKERS env var (e.g. GUNICORN_WORKERS=2).
_cores = multiprocessing.cpu_count()
workers = int(os.getenv("GUNICORN_WORKERS", str(2 * _cores + 1)))

# ---------------------------------------------------------------------------
# Worker class
# ---------------------------------------------------------------------------
# sync is fine — no WebSocket/SocketIO in this service.
# No monkey-patching needed.  Set GUNICORN_WORKER_CLASS=gevent if you
# need async I/O for concurrent long-running requests.
worker_class = os.getenv("GUNICORN_WORKER_CLASS", "sync")

# ---------------------------------------------------------------------------
# Listening socket
# ---------------------------------------------------------------------------
port = os.getenv("STRATEGY_PORT", "5007")
bind = os.getenv("GUNICORN_BIND", f"0.0.0.0:{port}")

# ---------------------------------------------------------------------------
# Timeouts
# ---------------------------------------------------------------------------
# High timeout (600s = 10 min) for model training endpoints:
#   POST /api/v1/train/rf  — trains on 90+ days of OHLCV data
#   POST /api/v1/train/lstm — trains LSTM for 25+ epochs
# These are CPU-bound and can take minutes.
# Override via GUNICORN_TIMEOUT for faster failure detection in dev.
timeout = int(os.getenv("GUNICORN_TIMEOUT", "600"))

# Graceful shutdown — wait for in-progress requests before killing workers
graceful_timeout = int(os.getenv("GUNICORN_GRACEFUL_TIMEOUT", "30"))

# Worker boot timeout — if a worker takes longer than this to start
# (e.g. loading ML models), gunicorn kills it and logs a CRITICAL message.
worker_timeout = int(os.getenv("GUNICORN_WORKER_TIMEOUT", "120"))

# ---------------------------------------------------------------------------
# Max requests — prevent memory leaks
# ---------------------------------------------------------------------------
# Restart each worker after handling this many requests to guard against
# gradual memory bloat (unclosed connections, cache growth, etc.).
max_requests = int(os.getenv("GUNICORN_MAX_REQUESTS", "10000"))
# Add jitter so workers don't all restart simultaneously.
max_requests_jitter = int(os.getenv("GUNICORN_MAX_REQUESTS_JITTER", "1000"))

# ---------------------------------------------------------------------------
# Preload — save memory by sharing the app across workers
# ---------------------------------------------------------------------------
# Load the application before forking workers.  Reduces per-worker memory
# via Copy-on-Write.  Disable if import-time side effects cause issues.
preload_app = os.getenv("GUNICORN_PRELOAD", "true").lower() in ("true", "1")

# ---------------------------------------------------------------------------
# Logging
# ---------------------------------------------------------------------------
accesslog = os.getenv("GUNICORN_ACCESS_LOG", "-")
errorlog = os.getenv("GUNICORN_ERROR_LOG", "-")
loglevel = os.getenv("GUNICORN_LOG_LEVEL", "info")

# Request log format — includes response time for performance monitoring
access_log_format = os.getenv(
    "GUNICORN_ACCESS_LOG_FORMAT",
    '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s "%(f)s" "%(a)s" %(L)s',
)

# ---------------------------------------------------------------------------
# Worker tmp dir
# ---------------------------------------------------------------------------
worker_tmp_dir = os.getenv("GUNICORN_WORKER_TMP_DIR", "/tmp/gunicorn_workers")

# ---------------------------------------------------------------------------
# Hooks
# ---------------------------------------------------------------------------


def on_starting(server):
    """Log worker configuration on startup."""
    server.log.info(
        "Trade Strategies — starting %s workers (%d CPU cores, class=%s, preload=%s, timeout=%s)",
        workers,
        _cores,
        worker_class,
        preload_app,
        timeout,
    )


def worker_abort(worker):
    """Log why a worker was killed (timeout, OOM, etc.)."""
    worker.log.warning("Worker %s aborted — likely timeout or OOM", worker.pid)


def post_worker_init(worker):
    """Log worker PID after successful initialisation."""
    worker.log.info("Worker %s initialised and ready", worker.pid)
