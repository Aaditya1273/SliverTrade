"""
Shared extensions for the SilverTrade Platform.

Initialises Flask extensions (SocketIO) and optional Redis client once,
so they can be imported by ``app.py``, blueprints, and services without
circular imports or duplication.
"""

import os
import logging

from flask_socketio import SocketIO

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# SocketIO
# ---------------------------------------------------------------------------

# Disable eventlet to prevent greenlet threading errors.
# This fixes concurrent order placement issues in Docker.
socketio = SocketIO(
    cors_allowed_origins="*",
    async_mode="threading",
    ping_timeout=10,
    ping_interval=5,
    logger=False,
    engineio_logger=False,
)

# ---------------------------------------------------------------------------
# Redis client (optional)
# ---------------------------------------------------------------------------

redis_client = None
"""Optional ``redis.Redis`` instance.  ``None`` when Redis is not configured."""


def init_redis() -> None:
    """Initialise the global ``redis_client`` from the ``REDIS_URL`` env var.

    Called once during ``create_app()``.  If ``REDIS_URL`` is empty or
    connection fails, ``redis_client`` stays ``None`` and all callers
    must handle that gracefully (see :func:`utils.redis_cache.get_cache`).
    """
    global redis_client

    redis_url = os.getenv("REDIS_URL", "")
    if not redis_url:
        logger.info("Redis not configured (REDIS_URL is empty) — skipping Redis initialisation")
        return

    try:
        import redis as _redis

        pool = _redis.ConnectionPool.from_url(
            redis_url,
            max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "50")),
            socket_timeout=int(os.getenv("REDIS_SOCKET_TIMEOUT", "2")),
            socket_connect_timeout=int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "2")),
            decode_responses=True,
        )
        client = _redis.Redis(connection_pool=pool)
        client.ping()  # verify connectivity
        redis_client = client
        logger.info(
            "Redis client connected to %s (pool=%d)",
            redis_url.split("@")[-1] if "@" in redis_url else redis_url,
            pool.max_connections,
        )
    except Exception as exc:
        redis_client = None
        logger.warning("Redis unavailable — falling back: %s", exc)
