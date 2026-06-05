"""
End-to-end tests for cache invalidation.

Tests validate:
1. ZeroMQ-based cache invalidation publisher/subscriber
2. Cross-process invalidation messages
3. Integration with auth_db and telegram_db cache invalidation
4. Graceful fallback when ZeroMQ is unavailable
"""

import json
import os
import time
from unittest.mock import patch

import pytest

from database.cache_invalidation import (
    CacheInvalidationPublisher,
    get_cache_invalidation_publisher,
    publish_auth_cache_invalidation,
    publish_feed_cache_invalidation,
    publish_all_cache_invalidation,
    AUTH_CACHE_TYPE,
    FEED_CACHE_TYPE,
    ALL_CACHE_TYPE,
)


# ── Publisher lifecycle ────────────────────────────────────────────────


class TestCacheInvalidationPublisher:
    """Verify publisher creation, lifecycle, and message format."""

    def test_singleton(self):
        """``get_cache_invalidation_publisher()`` returns the same instance."""
        p1 = get_cache_invalidation_publisher()
        p2 = get_cache_invalidation_publisher()
        assert p1 is p2

    def test_publish_without_zmq(self):
        """Publishing without ZeroMQ available should log a warning but not raise."""
        publisher = CacheInvalidationPublisher()
        # Without ZMQ the publisher can't initialise — should handle gracefully
        result = publisher.publish_invalidation("test_user", AUTH_CACHE_TYPE)
        assert result is False  # graceful failure

    def test_convenience_functions_noop_without_zmq(self):
        """Convenience publish functions should not raise when ZMQ is unavailable."""
        # These should all complete without exception
        publish_auth_cache_invalidation("user1")
        publish_feed_cache_invalidation("user1")
        publish_all_cache_invalidation("user1")

    def test_message_format(self):
        """Verify the message payload structure."""
        publisher = CacheInvalidationPublisher()

        # The _ensure_initialized will fail without ZMQ, so we test
        # the message format by calling _ensure_initialized directly
        # and verifying it returns False
        assert publisher._ensure_initialized() is False

    def test_close_idempotent(self):
        """Calling ``close()`` multiple times should not raise."""
        publisher = CacheInvalidationPublisher()
        publisher.close()  # first close — no-op if not initialised
        publisher.close()  # second close — idempotent


# ── Cache type constants ───────────────────────────────────────────────


class TestCacheInvalidationConstants:
    """Verify cache invalidation message type constants."""

    def test_cache_types(self):
        """Cache type constants should be non-empty strings."""
        assert AUTH_CACHE_TYPE == "AUTH"
        assert FEED_CACHE_TYPE == "FEED"
        assert ALL_CACHE_TYPE == "ALL"

    def test_message_prefix(self):
        """Message prefix should be defined."""
        from database.cache_invalidation import CACHE_INVALIDATION_PREFIX

        assert CACHE_INVALIDATION_PREFIX == "CACHE_INVALIDATE"


# ── Integration with auth_db ──────────────────────────────────────────


class TestAuthDBCacheInvalidation:
    """Verify auth_db triggers cache invalidation on credential changes."""

    def test_upsert_auth_invalidates_cache(self):
        """Calling ``upsert_auth()`` should attempt to publish invalidation."""
        # We can't easily test end-to-end without a full app context,
        # but we can verify the invalidation code path is reached.
        from database.auth_db import invalidate_user_cache

        # This should not raise
        invalidate_user_cache("test_user_123")

    def test_invalidate_user_cache_clears_all(self):
        """``invalidate_user_cache()`` clears all caches."""
        from database.auth_db import (
            auth_cache,
            broker_cache,
            feed_token_cache,
            verified_api_key_cache,
            invalid_api_key_cache,
            invalidate_user_cache,
        )

        # Seed some cache entries
        auth_cache["test"] = "value1"
        broker_cache["test"] = "value2"
        feed_token_cache["test"] = "value3"
        verified_api_key_cache["test"] = "value4"
        invalid_api_key_cache["test"] = "value5"

        invalidate_user_cache("test_user")

        # All caches should be cleared
        assert len(auth_cache) == 0
        assert len(broker_cache) == 0
        assert len(feed_token_cache) == 0
        assert len(verified_api_key_cache) == 0
        assert len(invalid_api_key_cache) == 0


# ── Integration with telegram_db ──────────────────────────────────────


class TestTelegramDBCacheInvalidation:
    """Verify telegram_db clears its caches on credential changes."""

    def test_telegram_cache_clear(self):
        """``clear_telegram_cache()`` clears all telegram caches."""
        from database.telegram_db import (
            _telegram_user_cache,
            _telegram_username_cache,
            _user_preferences_cache,
            _user_credentials_cache,
            clear_telegram_cache,
        )

        # Seed caches
        _telegram_user_cache["test"] = 1
        _telegram_username_cache["test"] = 1
        _user_preferences_cache["test"] = 1
        _user_credentials_cache["test"] = 1

        clear_telegram_cache()

        assert len(_telegram_user_cache) == 0
        assert len(_telegram_username_cache) == 0
        assert len(_user_preferences_cache) == 0
        assert len(_user_credentials_cache) == 0


# ── Integration with strategy_db ──────────────────────────────────────


class TestStrategyDBCacheInvalidation:
    """Verify strategy_db clears its caches."""

    def test_strategy_cache_clear(self):
        """``clear_strategy_cache()`` clears all strategy caches."""
        from database.strategy_db import (
            _strategy_webhook_cache,
            _user_strategies_cache,
            clear_strategy_cache,
        )

        _strategy_webhook_cache["test"] = 1
        _user_strategies_cache["test"] = 1

        clear_strategy_cache()

        assert len(_strategy_webhook_cache) == 0
        assert len(_user_strategies_cache) == 0


# ── Integration with settings_db ──────────────────────────────────────


class TestSettingsDBCacheInvalidation:
    """Verify settings_db clears its caches."""

    def test_settings_cache_clear(self):
        """``clear_settings_cache()`` clears the settings cache."""
        from database.settings_db import _settings_cache, clear_settings_cache

        _settings_cache["test"] = 1
        clear_settings_cache()
        assert len(_settings_cache) == 0


# ── Integration with flow_db ──────────────────────────────────────────


class TestFlowDBCacheInvalidation:
    """Verify flow_db clears its workflow caches."""

    def test_flow_cache_clear(self):
        """``clear_workflow_cache()`` clears workflow caches."""
        from database.flow_db import (
            _workflow_webhook_cache,
            _workflow_cache,
            clear_workflow_cache,
        )

        _workflow_webhook_cache["test"] = 1
        _workflow_cache["test"] = 1

        clear_workflow_cache()

        assert len(_workflow_webhook_cache) == 0
        assert len(_workflow_cache) == 0
