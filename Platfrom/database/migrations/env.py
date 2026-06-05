"""
SilverTrade AI — Multi-Database Alembic Environment

Supports schema migrations across all 5 database connections:
  - Main DB (auth, users, settings, strategies, symbols, telegram, flow, etc.)
  - Logs DB (traffic_logs, ip_bans, 404 tracker, API key tracker)
  - Latency DB (order_latency)
  - Health DB (health_metrics, health_alerts)
  - Sandbox DB (sandbox_orders, trades, positions, funds, GTT, config)

Usage:
  # Generate a migration for main database
  alembic -c database/alembic.ini revision --autogenerate \
      -m "add_user_preferences"

  # Apply migrations to all databases
  alembic -c database/alembic.ini upgrade head

  # Apply migrations to a specific database
  ALEMBIC_DB=logs alembic -c database/alembic.ini upgrade head
"""

import os
import sys
from logging.config import fileConfig

from alembic import context
from sqlalchemy import engine_from_config, pool

# ── Alembic Config ──────────────────────────────────────────────
config = context.config

# Set up Python path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), "..", ".."))

# ── Logging ─────────────────────────────────────────────────────
if config.config_file_name is not None:
    fileConfig(config.config_file_name)

# ── Database Selection ──────────────────────────────────────────
# Select which database to migrate via ALEMBIC_DB env var
# Options: main, logs, latency, health, sandbox (default: main)
DB_ALIAS = os.getenv("ALEMBIC_DB", "main").lower()

DB_CONFIGS = {
    "main": {
        "url_key": "DATABASE_URL",
        "schema": "public",
        "models_module": [
            "database.auth_db",
            "database.user_db",
            "database.settings_db",
            "database.strategy_db",
            "database.symbol",
            "database.telegram_db",
            "database.flow_db",
            "database.chartink_db",
            "database.chart_prefs_db",
            "database.market_calendar_db",
            "database.qty_freeze_db",
            "database.leverage_db",
            "database.strategy_portfolio_db",
            "database.master_contract_status_db",
            "database.action_center_db",
            "database.analyzer_db",
            "database.apilog_db",
        ],
        "base_class": "database.auth_db.Base",
    },
    "logs": {
        "url_key": "LOGS_DATABASE_URL",
        "schema": "logs",
        "models_module": ["database.traffic_db"],
        "base_class": "database.traffic_db.LogBase",
    },
    "latency": {
        "url_key": "LATENCY_DATABASE_URL",
        "schema": "latency",
        "models_module": ["database.latency_db"],
        "base_class": "database.latency_db.LatencyBase",
    },
    "health": {
        "url_key": "HEALTH_DATABASE_URL",
        "schema": "health",
        "models_module": ["database.health_db"],
        "base_class": "database.health_db.HealthBase",
    },
    "sandbox": {
        "url_key": "SANDBOX_DATABASE_URL",
        "schema": "sandbox",
        "models_module": ["database.sandbox_db"],
        "base_class": "database.sandbox_db.Base",
    },
}

if DB_ALIAS not in DB_CONFIGS:
    raise ValueError(
        f"Unknown ALEMBIC_DB: {DB_ALIAS!r}. "
        f"Options: {', '.join(DB_CONFIGS.keys())}"
    )

db_config = DB_CONFIGS[DB_ALIAS]
db_url = os.getenv(db_config["url_key"])

if not db_url:
    raise ValueError(
        f"{db_config['url_key']} is not set. "
        f"Cannot run migrations for '{DB_ALIAS}' database."
    )

print(f"🐘 Alembic: Migrating '{DB_ALIAS}' database via {db_config['url_key']}")
print(f"   Schema: {db_config['schema']}")
print(f"   URL: {db_url[:50]}...")

# ── Import models ───────────────────────────────────────────────
target_metadata = None

for module_name in db_config["models_module"]:
    try:
        __import__(module_name, fromlist=["Base"])
    except ImportError as e:
        print(f"   ⚠️  Could not import {module_name}: {e}")    # Get the declarative base for this database
    # Suppress logging during import — model modules may try to init DBs/start
    # background threads at import time, which is wasteful during migration
    import logging as _logging
    _logging.disable(_logging.CRITICAL)
    try:
        base_module_path, base_class_name = db_config["base_class"].rsplit(".", 1)
        base_module = __import__(base_module_path, fromlist=[base_class_name])
        base_class = getattr(base_module, base_class_name)
        target_metadata = base_class.metadata
        print(f"   ✅ Loaded models from: {db_config['base_class']}")
    except Exception as e:
        print(f"   ⚠️  Could not load base class: {e}")
        print(f"   Falling back to empty metadata")
        from sqlalchemy import MetaData
        target_metadata = MetaData()
    finally:
        _logging.disable(_logging.NOTSET)

    # Safety guard: autogenerate with empty metadata would drop ALL existing tables
    if target_metadata is None or (hasattr(target_metadata, 'tables') and len(target_metadata.tables) == 0):
        print("""
   ⚠️  WARNING: No tables in metadata!
   ➡️  Using --autogenerate will DROP ALL EXISTING TABLES in this schema!
   ➡️  Use 'alembic revision' (manual) or fix the model import instead.""")

    # Configure schema-qualified version table
    schema = db_config["schema"]
    if schema == "public":
        version_table = f"alembic_version_{DB_ALIAS}"
    else:
        version_table = f"{schema}.alembic_version_{DB_ALIAS}"


def run_migrations_offline() -> None:
    """Run migrations in 'offline' mode."""
    url = config.get_main_option("sqlalchemy.url")
    context.configure(
        url=url,
        target_metadata=target_metadata,
        literal_binds=True,
        dialect_opts={"paramstyle": "named"},
        version_table=version_table,
    )

    with context.begin_transaction():
        context.run_migrations()


def run_migrations_online() -> None:
    """Run migrations in 'online' mode."""
    # Override sqlalchemy.url with actual connection string from env
    section = config.get_section(config.config_ini_section)
    section["sqlalchemy.url"] = db_url

    connectable = engine_from_config(
        section,
        prefix="sqlalchemy.",
        poolclass=pool.NullPool,
    )

    with connectable.connect() as connection:
        # Set schema search path for this database
        if db_config["schema"] != "public":
            connection.exec_driver_sql(f"SET search_path TO {db_config['schema']}")

        context.configure(
            connection=connection,
            target_metadata=target_metadata,
            version_table=version_table,
            compare_type=True,
            compare_server_default=True,
        )

        with context.begin_transaction():
            context.run_migrations()

    connectable.dispose()


if context.is_offline_mode():
    run_migrations_offline()
else:
    run_migrations_online()
