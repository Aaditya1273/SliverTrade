"""Centralized database configuration for SilverTrade AI.

Supports SQLite, PostgreSQL, and MySQL with appropriate connection pooling
strategies for each database type. Provides a single point of configuration
for all database engines used across the platform.

Usage:
    from database.db_config import create_db_engine

    engine = create_db_engine("DATABASE_URL", "sqlite:///db/silvertrade.db")
"""

import os
from typing import Optional

from sqlalchemy import create_engine
from sqlalchemy.engine import Engine


def create_db_engine(
    db_url_key: str = "DATABASE_URL",
    default_url: str = "sqlite:///db/silvertrade.db",
    pool_size: int = 5,
    max_overflow: int = 10,
    pool_pre_ping: bool = True,
    pool_recycle: int = 3600,
) -> Engine:
    """Create a SQLAlchemy engine with appropriate pooling for the database type.

    Selects the optimal connection pool implementation based on the database URL:
    - SQLite:      NullPool (avoids connection exhaustion from concurrent access)
    - PostgreSQL:  QueuePool with configurable size + connection recycling
    - MySQL:       QueuePool with configurable size + connection recycling

    Args:
        db_url_key: Environment variable name containing the database URL.
        default_url: Default database URL if the env var is not set.
        pool_size: Number of connections to maintain in the pool (PG/MySQL).
        max_overflow: Maximum overflow connections beyond pool_size (PG/MySQL).
        pool_pre_ping: Whether to test connections for liveness before checkout.
        pool_recycle: Number of seconds after which to recycle connections.

    Returns:
        A configured SQLAlchemy Engine instance.

    Example:
        # SQLite (default)
        engine = create_db_engine()

        # PostgreSQL with custom pool
        engine = create_db_engine(
            "DATABASE_URL",
            pool_size=10,
            max_overflow=20,
        )

        # Read replica for analytics
        engine = create_db_engine(
            "ANALYTICS_DATABASE_URL",
            pool_size=3,
            max_overflow=5,
        )
    """
    db_url = os.getenv(db_url_key, default_url)

    if not db_url:
        raise ValueError(
            f"Database URL not found. Set {db_url_key} environment variable "
            f"or provide a default_url."
        )

    if "sqlite" in db_url:
        return _create_sqlite_engine(db_url)
    elif "postgresql" in db_url or "postgres" in db_url:
        return _create_postgres_engine(db_url, pool_size, max_overflow, pool_pre_ping, pool_recycle)
    else:
        # MySQL, MSSQL, or other - use QueuePool
        return _create_generic_engine(db_url, pool_size, max_overflow, pool_pre_ping, pool_recycle)


def _create_sqlite_engine(db_url: str) -> Engine:
    """Create a SQLite engine with NullPool to prevent connection exhaustion.

    SQLite has limited concurrency support - using NullPool ensures each
    connection is fresh and avoids "database is locked" errors from multiple
    threads sharing a single connection.

    Args:
        db_url: SQLite database URL (e.g. sqlite:///db/silvertrade.db)

    Returns:
        Configured SQLAlchemy Engine with NullPool.
    """
    from sqlalchemy.pool import NullPool

    # Ensure the directory for file-based SQLite databases exists
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
) -> Engine:
    """Create a PostgreSQL engine with QueuePool.

    Adds the psycopg2 driver if no driver is specified in the URL.
    Configures connection pooling for concurrent access.

    Args:
        db_url: PostgreSQL database URL
        pool_size: Number of connections to maintain in the pool
        max_overflow: Maximum overflow connections
        pool_pre_ping: Whether to test connections before checkout
        pool_recycle: Connection recycle time in seconds

    Returns:
        Configured SQLAlchemy Engine with QueuePool.
    """
    # Ensure a driver is specified (default to psycopg2)
    if "+psycopg2" not in db_url and "+asyncpg" not in db_url:
        db_url = db_url.replace("postgresql://", "postgresql+psycopg2://")
        db_url = db_url.replace("postgres://", "postgres+psycopg2://")

    return create_engine(
        db_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=pool_pre_ping,
        pool_recycle=pool_recycle,
        # Statement timeout (30 seconds)
        connect_args={"options": "-c statement_timeout=30000"},
    )


def _create_generic_engine(
    db_url: str,
    pool_size: int,
    max_overflow: int,
    pool_pre_ping: bool,
    pool_recycle: int,
) -> Engine:
    """Create a generic engine with QueuePool for MySQL/MSSQL/other databases.

    Args:
        db_url: Database URL
        pool_size: Number of connections to maintain in the pool
        max_overflow: Maximum overflow connections
        pool_pre_ping: Whether to test connections before checkout
        pool_recycle: Connection recycle time in seconds

    Returns:
        Configured SQLAlchemy Engine with QueuePool.
    """
    return create_engine(
        db_url,
        pool_size=pool_size,
        max_overflow=max_overflow,
        pool_pre_ping=pool_pre_ping,
        pool_recycle=pool_recycle,
    )


# Convenience alias for backward compatibility
create_engine_from_config = create_db_engine
