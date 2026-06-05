"""
Redis-backed cache service for distributed caching across multiple workers.

Provides a ``RedisCache`` class that wraps ``redis.Redis`` with automatic
connection pooling, graceful fallback to in-memory storage when Redis is
unavailable, and health-check methods for observability.

Usage:
    from utils.redis_cache import get_cache

    cache = get_cache()
    cache.set("mykey", {"nested": "value"}, ttl=300)
    value = cache.get("mykey")
    cache.delete("mykey")
    cache.clear("silvertrade:")

Graceful degradation:
    If Redis is not configured or unreachable, the cache silently falls back
    to an in-memory dict (per-process only).  Callers do not need to handle
    exceptions — the API is always available.
"""

import json
import logging
import os
import threading
import time
from datetime import timedelta
from typing import Any, Optional

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Fallback in-memory backend (used when Redis is unavailable)
# ---------------------------------------------------------------------------


class _MemoryBackend:
    """Thread-safe in-memory dict with TTL support — fallback when Redis is down."""

    def __init__(self) -> None:
        self._store: dict[str, tuple[float | None, str]] = {}  # key → (expires_at, json_value)
        self._lock = threading.Lock()

    def get(self, key: str) -> Optional[Any]:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return None
            expires_at, json_value = entry
            if expires_at is not None and time.monotonic() > expires_at:
                del self._store[key]
                return None
            return json.loads(json_value)

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        expires_at = (time.monotonic() + ttl) if ttl is not None else None
        with self._lock:
            self._store[key] = (expires_at, json.dumps(value, default=str))
        return True

    def delete(self, key: str) -> bool:
        with self._lock:
            existed = key in self._store
            self._store.pop(key, None)
        return existed

    def exists(self, key: str) -> bool:
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                return False
            expires_at, _ = entry
            if expires_at is not None and time.monotonic() > expires_at:
                del self._store[key]
                return False
            return True

    def clear(self, prefix: str = "") -> int:
        """Remove all keys matching *prefix*.  Returns count of removed keys."""
        with self._lock:
            if not prefix:
                count = len(self._store)
                self._store.clear()
                return count
            keys = [k for k in self._store if k.startswith(prefix)]
            for k in keys:
                del self._store[k]
            return len(keys)

    def size(self) -> int:
        with self._lock:
            return len(self._store)

    def get_all(self, prefix: str = "") -> dict[str, Any]:
        """Return all entries matching *prefix* as a dict."""
        result = {}
        with self._lock:
            for key, (expires_at, json_value) in self._store.items():
                if prefix and not key.startswith(prefix):
                    continue
                if expires_at is not None and time.monotonic() > expires_at:
                    continue
                result[key] = json.loads(json_value)
        return result

    def incr(self, key: str, amount: int = 1) -> int:
        """Increment a counter.  Returns the new value."""
        with self._lock:
            entry = self._store.get(key)
            if entry is None:
                val = amount
            else:
                _, json_value = entry
                val = json.loads(json_value) + amount
            self._store[key] = (None, json.dumps(val))
        return val


# ---------------------------------------------------------------------------
# Redis cache
# ---------------------------------------------------------------------------


class RedisCache:
    """Redis-backed cache with in-memory fallback.

    Thread-safe.  All public methods return without raising on Redis errors
    — they fall through to the memory backend instead.

    Parameters
    ----------
    redis_url:
        Redis connection URL, e.g. ``redis://:password@localhost:6379/0``.
        If empty or ``None``, only the memory backend is used.
    default_ttl:
        Default TTL in seconds when ``set()`` is called without an explicit
        ``ttl``.  ``None`` means no expiry.
    key_prefix:
        Optional prefix prepended to every key (e.g. ``"silvertrade:"``).
    max_connections:
        Maximum connections in the Redis connection pool.
    socket_timeout:
        Socket timeout in seconds for Redis operations.
    socket_connect_timeout:
        Connection timeout in seconds.
    """

    def __init__(
        self,
        redis_url: str = "",
        default_ttl: Optional[int] = 300,
        key_prefix: str = "silvertrade:",
        max_connections: int = 50,
        socket_timeout: int = 2,
        socket_connect_timeout: int = 2,
    ) -> None:
        self._redis_url = redis_url
        self._default_ttl = default_ttl
        self._key_prefix = key_prefix
        self._memory = _MemoryBackend()
        self._redis: Any = None  # redis.Redis instance
        self._redis_available = False
        self._lock = threading.Lock()

        if redis_url:
            self._connect(
                max_connections=max_connections,
                socket_timeout=socket_timeout,
                socket_connect_timeout=socket_connect_timeout,
            )

    def _connect(
        self,
        max_connections: int,
        socket_timeout: int,
        socket_connect_timeout: int,
    ) -> None:
        """Lazy-init the Redis client with a connection pool."""
        try:
            import redis as _redis

            pool = _redis.ConnectionPool.from_url(
                self._redis_url,
                max_connections=max_connections,
                socket_timeout=socket_timeout,
                socket_connect_timeout=socket_connect_timeout,
                decode_responses=True,
            )
            client = _redis.Redis(connection_pool=pool)
            # Verify connectivity with a lightweight command
            client.ping()
            self._redis = client
            self._redis_available = True
            logger.info(
                "Redis cache connected to %s (pool=%d)",
                self._redis_url.split("@")[-1] if "@" in self._redis_url else self._redis_url,
                max_connections,
            )
        except Exception as exc:
            self._redis_available = False
            self._redis = None
            logger.warning("Redis cache unavailable — falling back to in-memory: %s", exc)

    def _prefixed(self, key: str) -> str:
        return f"{self._key_prefix}{key}"

    # -- public API ---------------------------------------------------------

    @property
    def available(self) -> bool:
        """Whether Redis is connected and responsive."""
        return self._redis_available

    @property
    def using_memory(self) -> bool:
        """Whether the in-memory fallback is currently active."""
        return not self._redis_available

    def get(self, key: str) -> Any:
        """Retrieve a value by key.  Returns ``None`` if missing or expired."""
        if self._redis_available and self._redis is not None:
            try:
                raw = self._redis.get(self._prefixed(key))
                if raw is None:
                    return None
                return json.loads(raw)
            except Exception:
                self._degrade()
        return self._memory.get(self._prefixed(key))

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Store a value.  Uses *ttl* seconds or the default TTL."""
        if ttl is None:
            ttl = self._default_ttl
        payload = json.dumps(value, default=str)
        if self._redis_available and self._redis is not None:
            try:
                prefixed = self._prefixed(key)
                if ttl is not None:
                    return bool(self._redis.setex(prefixed, ttl, payload))
                return bool(self._redis.set(prefixed, payload))
            except Exception:
                self._degrade()
        return self._memory.set(self._prefixed(key), value, ttl)

    def delete(self, key: str) -> bool:
        """Delete a key.  Returns ``True`` if it existed."""
        deleted = False
        if self._redis_available and self._redis is not None:
            try:
                deleted = bool(self._redis.delete(self._prefixed(key)))
            except Exception:
                self._degrade()
        # Also clean memory backend in case Redis was used before degrade
        return self._memory.delete(self._prefixed(key)) or deleted

    def exists(self, key: str) -> bool:
        """Check if a key exists and is not expired."""
        if self._redis_available and self._redis is not None:
            try:
                return bool(self._redis.exists(self._prefixed(key)))
            except Exception:
                self._degrade()
        return self._memory.exists(self._prefixed(key))

    def clear(self, prefix: str = "") -> int:
        """Remove all keys matching *prefix*.

        The *prefix* is appended after the key prefix, so
        ``clear("session:")`` removes ``silvertrade:session:*``.
        """
        count = 0
        if self._redis_available and self._redis is not None:
            try:
                pattern = self._prefixed(prefix) + "*"
                cursor = 0
                while True:
                    cursor, keys = self._redis.scan(cursor, match=pattern, count=500)
                    if keys:
                        count += self._redis.delete(*keys)
                    if cursor == 0:
                        break
            except Exception:
                self._degrade()
        return count + self._memory.clear(self._prefixed(prefix))

    def incr(self, key: str, amount: int = 1) -> int:
        """Atomically increment a counter.  Returns the new value."""
        if self._redis_available and self._redis is not None:
            try:
                return int(self._redis.incr(self._prefixed(key), amount))
            except Exception:
                self._degrade()
        return self._memory.incr(self._prefixed(key), amount)

    def health(self) -> dict:
        """Return a health-check dict for observability."""
        result: dict[str, Any] = {
            "available": self._redis_available,
            "using_memory": self.using_memory,
            "key_prefix": self._key_prefix,
            "memory_entries": self._memory.size(),
        }
        if self._redis_available and self._redis is not None:
            try:
                info = self._redis.info(section="server")
                result["redis_version"] = info.get("server", {}).get("redis_version", "unknown")
                result["connected_clients"] = info.get("clients", {}).get(
                    "connected_clients", "N/A"
                )
                result["used_memory_human"] = info.get("memory", {}).get(
                    "used_memory_human", "N/A"
                )
                result["uptime_in_seconds"] = info.get("server", {}).get(
                    "uptime_in_seconds", 0
                )
                dbsize = self._redis.dbsize()
                result["total_keys"] = dbsize
            except Exception as exc:
                result["error"] = str(exc)
                result["available"] = False
        return result

    def _degrade(self) -> None:
        """Gracefully degrade to in-memory backend on Redis error."""
        with self._lock:
            if self._redis_available:
                self._redis_available = False
                self._redis = None
                logger.warning("Redis connection lost — falling back to in-memory cache")


# ---------------------------------------------------------------------------
# Singleton helpers
# ---------------------------------------------------------------------------

_cache_instance: Optional[RedisCache] = None
_cache_lock = threading.Lock()


def get_cache() -> RedisCache:
    """Return the singleton ``RedisCache`` instance.

    Configured from environment variables:

    * ``REDIS_URL`` — Redis connection URL (default ``""`` → memory-only)
    * ``REDIS_KEY_PREFIX`` — key prefix (default ``"silvertrade:"``)
    * ``REDIS_MAX_CONNECTIONS`` — pool size (default ``50``)
    * ``REDIS_SOCKET_TIMEOUT`` — socket timeout seconds (default ``2``)
    * ``REDIS_DEFAULT_TTL`` — default TTL seconds (default ``300``)
    """
    global _cache_instance
    if _cache_instance is None:
        with _cache_lock:
            if _cache_instance is None:
                _cache_instance = RedisCache(
                    redis_url=os.getenv("REDIS_URL", ""),
                    default_ttl=int(os.getenv("REDIS_DEFAULT_TTL", "300")),
                    key_prefix=os.getenv("REDIS_KEY_PREFIX", "silvertrade:"),
                    max_connections=int(os.getenv("REDIS_MAX_CONNECTIONS", "50")),
                    socket_timeout=int(os.getenv("REDIS_SOCKET_TIMEOUT", "2")),
                    socket_connect_timeout=int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", "2")),
                )
    return _cache_instance


def reset_cache() -> None:
    """Reset the singleton (for testing)."""
    global _cache_instance
    with _cache_lock:
        _cache_instance = None
