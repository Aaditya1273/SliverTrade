"""Rate limiting configuration for SilverTrade AI.

Supports two storage backends:
- **In-memory** (``memory://``) — default, suitable for single-worker dev.
- **Redis** (``redis://...``) — required for 1000+ concurrent users across
  multiple gunicorn workers.  Set ``RATE_LIMIT_STORAGE_URL`` in .env.

When no ``RATE_LIMIT_STORAGE_URL`` is set, the in-memory backend is used.
When set to a Redis URL, the ``limits`` library uses a shared Redis instance
so rate-limit counters are consistent across all workers.

Usage:
    from limiter import limiter

    @limiter.limit("5 per minute")
    def my_route():
        ...
"""

import os

from flask_limiter import Limiter
from flask_limiter.util import get_remote_address

# Storage URI: environment variable or fall back to in-memory.
# Examples:
#   RATE_LIMIT_STORAGE_URL=redis://:password@localhost:6379/0
#   RATE_LIMIT_STORAGE_URL=redis+sentinel://localhost:26379/service_name
#   RATE_LIMIT_STORAGE_URL=memory://                    (default)
_storage_uri = os.getenv("RATE_LIMIT_STORAGE_URL", "memory://")

limiter = Limiter(
    key_func=get_remote_address,
    storage_uri=_storage_uri,
    strategy="moving-window",
)
