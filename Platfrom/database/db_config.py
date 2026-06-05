"""Centralized database configuration for SilverTrade AI.

Supports SQLite, PostgreSQL, and MySQL with appropriate connection pooling
strategies for each database type. Provides a single point of configuration
for all database engines used across the platform.

Key scalability features for 1000+ concurrent users:
- **Engine memoization**: engines are cached by (URL, pool_config) so 18+
  database modules sharing the same ``DATABASE_URL`` reuse a single
  connection pool instead of creating 18 independent ones.
- **Env-var-driven pool sizing**: ``POOL_SIZE``, ``MAX_OVERFLOW``,
  ``POOL_TIMEOUT``, ``POOL_RECYCLE`` environment variables override defaults.
- **Pool health monitoring**: ``get_pool_stats()`` returns per-engine pool
  utilization metrics for observability dashboards.

Usage:
    from database.db_config import get_db_engine, get_pool_stats

    engine = get_db_engine("DATABASE_URL")
    engine = get_db_engine("LOGS_DATABASE_URL", pool_size=20)

    # In production (PostgreSQL) — env vars control pool sizing:
    #   POOL_SIZE=50 MAX_OVERFLOW=100 POOL_TIMEOUT=30
"""

import os
import threading
from typing import Dict, Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


# ---------------------------------------------------------------------------
# Memoisation: one engine per (URL, pool_size, max_overflow) tuple.
# This is critical for 1000+ concurrent users — without it, 18 database
# modules each calling ``create_engine("DATABASE_URL", …)`` would open
# 18 × (pool_size + max_overflow) connections to the same database,
# easily exhausting PG's ``max_connections``.
# ---------------------------------------------------------------------------
_engine_cache: Dict[str, Engine] = {}
_cache_lock = threading.Lock()


def _cache_key(
    db_url: str,
    pool_size: int,
    max_overflow: int,
    pool_timeout: int,
    pool_pre_ping: bool,
    pool_recycle: int,
) -> str:
    """Deterministic key for the engine cache."""
    return (
        f"{db_url}|pool={pool_size}|overflow={max_overflow}"
        f"|timeout={pool_timeout}|ping={pool_pre_ping}|recycle={pool_recycle}"
    )


# ---------------------------------------------------------------------------
# Env-var defaults — tuned for 1000+ concurrent users with PG.
# Users override via environment variables without touching code.
# ---------------------------------------------------------------------------
def _env_pool_size(default: int) -> int:
    try:
        return int(os.environ["POOL_SIZE"])
    except (KeyError, ValueError):
        return default


def _env_max_overflow(default: int) -> int:
    try:
        return int(os.environ["MAX_OVERFLOW"])
    except (KeyError, ValueError):
        return default


def _env_pool_timeout(default: int) -> int:
    try:
        return int(os.environ["POOL_TIMEOUT"])
    except (KeyError, ValueError):
        return default


def _env_pool_recycle(default: int) -> int:
    try:
        return int(os.environ["POOL_RECYCLE"])
    except (KeyError, ValueError):
        return default


def _env_pool_pre_ping(default: bool) -> bool:
    val = os.environ.get("POOL_PRE_PING")
    if val is None:
        return default
    return val.lower() in ("true", "1", "yes")


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------


def get_db_engine(
    db_url_key: str = "DATABASE_URL",
    default_url: str = "sqlite:///db/silvertrade.db",
    pool_size: Optional[int] = None,
    max_overflow: Optional[int] = None,
    pool_timeout: Optional[int] = None,
    pool_pre_ping: Optional[bool] = None,
    pool_recycle: Optional[int] = None,
) -> Engine:
    """Return a memoised SQLAlchemy Engine for the given database URL key.

    Engines are cached by their resolved URL + pool config so that all
    modules referencing the same ``DATABASE_URL`` share a single connection
    pool.  Environment variables ``POOL_SIZE``, ``MAX_OVERFLOW``,
    ``POOL_TIMEOUT``, ``POOL_PRE_PING``, and ``POOL_RECYCLE`` override the
    defaults globally; per-call arguments override env vars.

    Parameters
    ----------
    db_url_key : str
        Environment variable name holding the database URL.
    default_url : str
        Fallback URL if the env var is unset.
    pool_size : int or None
        Connections kept in the pool (PG/MySQL).  Falls back to the
        ``POOL_SIZE`` env var, then to a PG-sensible default of ``50``.
    max_overflow : int or None
        Overflow connections beyond *pool_size*.  Falls back to
        ``MAX_OVERFLOW`` env var, then ``100``.
    pool_timeout : int or None
        Seconds to wait for a connection before raising
        ``TimeoutError``.  Falls back to ``POOL_TIMEOUT`` env var, then
        ``30``.
    pool_pre_ping : bool or None
        Whether to test connections for liveness before checkout.
        Falls back to ``POOL_PRE_PING`` env var, then ``True``.
    pool_recycle : int or None
        Seconds after which to recycle connections. Falls back to
        ``POOL_RECYCLE`` env var, then ``3600``.

    Returns
    -------
    Engine
        A configured SQLAlchemy Engine instance (shared/cached).
    """
    db_url = os.getenv(db_url_key, default_url)
    if not db_url:
        raise ValueError(
            f"Database URL not found. Set {db_url_key} environment variable "
            f"or provide a default_url."
        )

    # Resolve each parameter: per-call arg > env var > built-in default
    _ps = pool_size if pool_size is not None else _env_pool_size(50)
    _mo = max_overflow if max_overflow is not None else _env_max_overflow(100)
    _pt = pool_timeout if pool_timeout is not None else _env_pool_timeout(30)
    _pp = pool_pre_ping if pool_pre_ping is not None else _env_pool_pre_ping(True)
    _pr = pool_recycle if pool_recycle is not None else _env_pool_recycle(3600)

    key = _cache_key(db_url, _ps, _mo, _pt, _pp, _pr)

    with _cache_lock:
        if key in _engine_cache:
            return _engine_cache[key]

        if "sqlite" in db_url:
            engine = _create_sqlite_engine(db_url)
        elif "postgresql" in db_url or "postgres" in db_url:
            engine = _create_postgres_engine(db_url, _ps, _mo, _pp, _pr, _pt)
        else:
            engine = _create_generic_engine(db_url, _ps, _mo, _pp, _pr, _pt)

        _engine_cache[key] = engine
        return engine


def get_pool_stats() -> dict:
    """Return utilisation metrics for all cached engines.

    Useful for Prometheus /health endpoints and capacity planning.
    Returns an empty dict when SQLite is in use (NullPool has no metrics).

    Example return value::

        {
          "sqlite:///db/silvertrade.db": {
            "driver": "sqlite",
            "pool_class": "NullPool",
            "note": "No pool metrics for NullPool"
          },
          "postgresql+psycopg2://...": {
            "driver": "postgresql",
            "pool_class": "QueuePool",
            "size": 50,
            "overflow": 10,
            "checkedin": 48,
            "checkedout": 2,
            "pool_timeout": 30,
            "in_use_pct": 3.3,
          }
        }
    """
    with _cache_lock:
        stats = {}
        for key, engine in _engine_cache.items():
            url_str = str(engine.url)
            pool = engine.pool
            info: dict = {
                "driver": engine.dialect.name,
                "pool_class": type(pool).__name__,
            }

            # QueuePool reports runtime metrics; NullPool does not.
            if hasattr(pool, "size"):
                checkedin = getattr(pool, "checkedin", 0)
                checkedout = getattr(pool, "checkedout", 0)
                total = pool.size() + pool.overflow()
                in_use = (checkedout / total * 100) if total > 0 else 0.0
                info.update(
                    size=pool.size(),
                    overflow=pool.overflow(),
                    checkedin=checkedin,
                    checkedout=checkedout,
                    pool_timeout=getattr(pool, "_timeout", None),
                    in_use_pct=round(in_use, 1),
                )
            else:
                info["note"] = "No pool metrics for NullPool"

            # Short label: use the cache-key prefix for readability
            label = key.split("|")[0] if "|" in key else url_str
            stats[label] = info

        return stats


def clear_engine_cache() -> None:
    """Dispose of all cached engines and clear the cache.

    Called during graceful shutdown to release database connections.
    """
    with _cache_lock:
        for key, engine in _engine_cache.items():
            try:
                engine.dispose()
            except Exception:
                pass
        _engine_cache.clear()


# ---------------------------------------------------------------------------
# Internal helpers
# ---------------------------------------------------------------------------


def _create_sqlite_engine(db_url: str) -> Engine:
    """Create a SQLite engine with NullPool."""
    from sqlalchemy.pool import NullPool

    if ":memory:" not in db_url:
        db_path = db_url.replace("sqlite:///", "")
        if db_path:
            db_dir = os.path.dirname(db_path)
            if db_dir:
                os.makedirs(db_dir, exist_ok=True)

    return create_engine(
        db_url,
        poolclass=NullPool,
        connect_args={"check_same_thread": False},
    )


def _create_postgres_engine(
    db_url: str,
    pool_size: int,
    max_overflow: int,
    pool_pre_ping: bool,
    pool_recycle: int,
    pool_timeout: int,
) -> Engine:
    """Create a PostgreSQL engine with QueuePool."""
    if "+psycopg2" not in db_url and "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://")
        db_url = db_url.replace("postgres://", "postgres+psycopg2://")

    return create_engine(
        db_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=pool_pre_ping,
        pool_recycle=pool_recycle,
        pool_timeout=pool_timeout,
        connect_args={"options": "-c statement_timeout=30000"},
    )


def _create_generic_engine(
    db_url: str,
    pool_size: int,
    max_overflow: int,
    pool_pre_ping: bool,
    pool_recycle: int,
    pool_timeout: int,
) -> Engine:
    """Create a generic engine with QueuePool for MySQL/MSSQL/other DBs."""
    return create_engine(
        db_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=pool_pre_ping,
        pool_recycle=pool_recycle,
        pool_timeout=pool_timeout,
    )


# Backward-compatible aliases (kept for existing importers)
create_db_engine = get_db_engine
create_engine_from_config = get_db_engine
