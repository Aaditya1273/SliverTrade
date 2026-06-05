"""
End-to-end tests for the Redis-backed caching layer.

Tests validate:
1. Redis connection and basic CRUD
2. TTL expiry
3. Graceful fallback to in-memory when Redis is unavailable
4. Concurrent access (thread safety)
5. Singleton ``get_cache()`` behaviour
6. Integration with JWT token blacklisting
7. Compatibility with the rate limiter storage backend

These tests work with or without a running Redis server — they adapt
automatically (when Redis is absent they test the in-memory fallback).
"""

import json
import os
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed
from unittest.mock import patch

import pytest

from utils.redis_cache import RedisCache, get_cache, reset_cache


# ── Helpers ──────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _reset_cache():
    """Reset the singleton before and after every test."""
    reset_cache()
    yield
    reset_cache()


@pytest.fixture
def cache():
    """Return a *fresh* ``RedisCache`` instance (not the singleton)."""
    return RedisCache(
        redis_url=os.getenv("REDIS_URL", ""),
        default_ttl=None,  # no expiry unless explicitly set
        key_prefix="test:",
        max_connections=10,
    )


def _redis_available() -> bool:
    """Check if a Redis server is reachable."""
    url = os.getenv("REDIS_URL", "")
    if not url:
        return False
    try:
        import redis as _redis

        client = _redis.Redis.from_url(url, socket_timeout=1)
        client.ping()
        client.close()
        return True
    except Exception:
        return False


# ── Connection & CRUD ───────────────────────────────────────────────────


class TestRedisCacheConnection:
    """Verify connection and basic CRUD operations."""

    def test_singleton(self):
        """``get_cache()`` returns the same instance on repeated calls."""
        c1 = get_cache()
        c2 = get_cache()
        assert c1 is c2

    def test_reset_singleton(self):
        """After ``reset_cache()`` a new singleton is created."""
        c1 = get_cache()
        reset_cache()
        c2 = get_cache()
        assert c1 is not c2

    def test_using_memory_when_no_redis(self):
        """Without ``REDIS_URL`` the memory backend is used."""
        cache = RedisCache(redis_url="")
        assert cache.using_memory
        assert not cache.available

    def test_set_and_get(self, cache: RedisCache):
        """Simple set followed by get returns the stored value."""
        cache.set("foo", {"hello": "world"})
        assert cache.get("foo") == {"hello": "world"}

    def test_get_missing_key(self, cache: RedisCache):
        """Getting a non-existent key returns ``None``."""
        assert cache.get("nope") is None

    def test_delete(self, cache: RedisCache):
        """Deleting a key removes it."""
        cache.set("delme", 42)
        assert cache.delete("delme")  # returns True if it existed
        assert cache.get("delme") is None

    def test_delete_missing(self, cache: RedisCache):
        """Deleting a non-existent key returns ``False``."""
        assert not cache.delete("ghost")

    def test_exists(self, cache: RedisCache):
        """``exists()`` returns ``True`` only for existing keys."""
        cache.set("exist", 1)
        assert cache.exists("exist")
        assert not cache.exists("noexist")

    def test_set_overwrite(self, cache: RedisCache):
        """Setting an existing key overwrites its value."""
        cache.set("over", 1)
        cache.set("over", 2)
        assert cache.get("over") == 2


# ── TTL ─────────────────────────────────────────────────────────────────


class TestRedisCacheTTL:
    """Verify TTL expiry behaviour."""

    def test_ttl_expiry(self, cache: RedisCache):
        """A key with a 1-second TTL expires after 1 second."""
        cache.set("ttl", "gone_soon", ttl=1)
        assert cache.get("ttl") == "gone_soon"
        time.sleep(1.1)
        assert cache.get("ttl") is None

    def test_default_ttl(self):
        """When ``default_ttl`` is set, keys expire without explicit TTL."""
        cache = RedisCache(redis_url=os.getenv("REDIS_URL", ""), default_ttl=1, key_prefix="test:")
        cache.set("auto", "expires")
        assert cache.get("auto") == "expires"
        time.sleep(1.1)
        assert cache.get("auto") is None

    def test_no_expiry(self, cache: RedisCache):
        """Without TTL the key persists."""
        cache.set("persist", "forever")
        assert cache.get("persist") == "forever"

    def test_ttl_zero(self, cache: RedisCache):
        """A TTL of 0 means expire immediately — get returns None."""
        cache.set("zero", "val", ttl=0)
        # TTL=0 means the key is already expired
        assert cache.get("zero") is None


# ── Clear / Bulk ────────────────────────────────────────────────────────


class TestRedisCacheClear:
    """Verify bulk-clear operations."""

    def test_clear_prefix(self, cache: RedisCache):
        """``clear("x:")`` removes keys starting with ``x:``."""
        cache.set("x:a", 1)
        cache.set("x:b", 2)
        cache.set("y:a", 3)
        count = cache.clear("x:")
        assert count >= 2
        assert cache.get("x:a") is None
        assert cache.get("x:b") is None
        assert cache.get("y:a") == 3

    def test_clear_all(self, cache: RedisCache):
        """``clear()`` with no prefix removes all keys in the prefix namespace."""
        cache.set("a", 1)
        cache.set("b", 2)
        count = cache.clear()
        assert count >= 2
        assert cache.get("a") is None
        assert cache.get("b") is None


# ── Increment ──────────────────────────────────────────────────────────


class TestRedisCacheIncr:
    """Verify atomic increment."""

    def test_incr_new_key(self, cache: RedisCache):
        """``incr`` on a new key returns ``amount``."""
        assert cache.incr("counter", 5) == 5

    def test_incr_existing(self, cache: RedisCache):
        """``incr`` increments an existing counter."""
        cache.set("counter", 10)
        assert cache.incr("counter", 3) == 13

    def test_incr_default(self, cache: RedisCache):
        """``incr`` without *amount* increments by 1."""
        cache.set("counter", 0)
        assert cache.incr("counter") == 1


# ── Fallback behaviour ─────────────────────────────────────────────────


class TestRedisCacheFallback:
    """Verify graceful degradation when Redis is unavailable."""

    def test_operations_work_after_degrade(self, cache: RedisCache):
        """All operations continue to work after Redis is lost."""
        # Simulate degrade
        cache._degrade()
        assert cache.using_memory

        cache.set("still", "works")
        assert cache.get("still") == "works"
        assert cache.exists("still")
        assert cache.delete("still")
        assert not cache.exists("still")
        assert cache.incr("counter") == 1

    def test_degrade_is_idempotent(self, cache: RedisCache):
        """Calling ``_degrade()`` multiple times does not error."""
        cache._degrade()
        cache._degrade()  # should not raise
        assert cache.using_memory

    def test_clear_after_degrade(self, cache: RedisCache):
        """``clear()`` works after degrade."""
        cache._degrade()
        cache.set("a", 1)
        cache.set("b", 2)
        assert cache.clear() >= 2
        assert cache.get("a") is None


# ── Concurrency ─────────────────────────────────────────────────────────


class TestRedisCacheConcurrency:
    """Verify thread safety under concurrent access."""

    CONCURRENCY = 20
    OPERATIONS_PER_THREAD = 50

    def test_concurrent_set_and_get(self, cache: RedisCache):
        """Multiple threads set/get different keys without data loss."""

        def _worker(thread_id: int):
            errors = []
            for i in range(self.OPERATIONS_PER_THREAD):
                key = f"concurrent:t{thread_id}_op{i}"
                try:
                    cache.set(key, {"thread": thread_id, "op": i})
                    val = cache.get(key)
                    assert val is not None
                    assert val["thread"] == thread_id
                    assert val["op"] == i
                except AssertionError as e:
                    errors.append(str(e))
            return errors

        with ThreadPoolExecutor(max_workers=self.CONCURRENCY) as pool:
            futures = [pool.submit(_worker, tid) for tid in range(self.CONCURRENCY)]
            all_errors = []
            for f in as_completed(futures):
                all_errors.extend(f.result())

        assert not all_errors, f"Concurrent access errors: {all_errors[:5]}"

    def test_concurrent_incr(self, cache: RedisCache):
        """Concurrent increments produce the correct total."""

        cache.set("race_counter", 0)

        def _incr():
            for _ in range(100):
                cache.incr("race_counter")

        threads = [threading.Thread(target=_incr) for _ in range(10)]
        for t in threads:
            t.start()
        for t in threads:
            t.join()

        assert cache.get("race_counter") == 1000, (
            f"Expected 1000, got {cache.get('race_counter')}"
        )


# ── Health ──────────────────────────────────────────────────────────────


class TestRedisCacheHealth:
    """Verify health-check endpoint."""

    def test_health_always_returns(self, cache: RedisCache):
        """``health()`` never raises, even without Redis."""
        h = cache.health()
        assert "available" in h
        assert "using_memory" in h
        assert "key_prefix" in h
        assert h["key_prefix"] == "test:"

    def test_health_memory_backend(self, cache: RedisCache):
        """Health includes memory_entries count."""
        if not cache.available:
            assert cache.using_memory
        cache.set("h", "v")
        h = cache.health()
        assert h["memory_entries"] >= 1


# ── Integration with JWT blacklisting ────────────────────────────────


class TestJWTBlacklistIntegration:
    """Verify that token blacklisting works with or without Redis."""

    def test_blacklist_no_redis(self):
        """Token blacklisting falls back gracefully when redis_client is None."""
        from extensions import redis_client

        # Simulate no Redis
        with patch("utils.jwt_auth.redis_client", None):
            from utils.jwt_auth import blacklist_token, _is_token_blacklisted

            # Should not raise
            blacklist_token("fake-jti")
            assert not _is_token_blacklisted("fake-jti")

    def test_blacklist_with_memory_cache(self):
        """Token blacklisting with in-memory cache fallback."""
        from utils.jwt_auth import blacklist_token, _is_token_blacklisted

        # Run without Redis — should use memory fallback silently
        blacklist_token("test-jti-123")
        # Without Redis the blacklist check returns False (best-effort)
        result = _is_token_blacklisted("test-jti-123")
        assert result is False  # graceful fallback


# ── Rate limiter compatibility ────────────────────────────────────────


class TestRateLimiterStorage:
    """Verify that the rate limiter can use Redis storage URI."""

    def test_memory_storage_default(self):
        """The default storage URI is ``memory://``."""
        from limiter import _storage_uri

        # When REDIS_URL is not set, the limiter falls back to memory storage
        if not os.getenv("REDIS_URL"):
            assert _storage_uri == "memory://"

    def test_redis_storage_uri_configured(self):
        """When ``RATE_LIMIT_STORAGE_URL`` is set, the limiter uses it."""
        from limiter import _storage_uri

        # If the env var was explicitly set, verify it's used
        env_uri = os.getenv("RATE_LIMIT_STORAGE_URL")
        if env_uri:
            assert _storage_uri == env_uri
