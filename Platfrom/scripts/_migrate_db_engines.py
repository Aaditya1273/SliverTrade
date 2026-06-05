#!/usr/bin/env python3
"""Migrate all database modules to use ``db_config.get_db_engine()``.

Each file follows the same pattern and this script replaces the engine-
creation block in-place while keeping everything else (imports, sessions,
declarative base, model classes, CRUD functions) intact.

Safe to re-run — idempotent (checks whether the file already uses
``get_db_engine`` before making changes).
"""

import os
import re
import sys

PROJECT = os.path.abspath(os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))  # Platfrom/
DB_DIR = os.path.join(PROJECT, "database")

# ---------------------------------------------------------------------------
# Per-file replacement rules: (filename, old_block, new_block)
# ---------------------------------------------------------------------------
REPLACEMENTS: list[tuple[str, str, str]] = []


def _add(
    path: str,
    old: str,
    new: str,
    *,
    remove_imports: tuple[str, ...] = (),
):
    """Register a replacement for *path*.

    If *remove_imports* is given, those import lines are removed from the
    file on the first pass (but only when they aren't used elsewhere).
    """
    full = os.path.join(DB_DIR, path) if not path.startswith("/") else path
    REPLACEMENTS.append((full, old, new, remove_imports))


# ============================ STANDARD PATTERN ============================
# The majority of database modules share DATABASE_URL with the same
# ``if "sqlite" … else QueuePool(50, 100)`` branching.
# The ``echo=False`` variants differ only by that parameter.

_STANDARD_SQLITE = """
if DATABASE_URL and "sqlite" in DATABASE_URL:
    # SQLite: Use NullPool to prevent connection pool exhaustion
    engine = create_engine(
        DATABASE_URL, poolclass=NullPool, connect_args={"check_same_thread": False}
    )
else:
    # For other databases like PostgreSQL, use connection pooling
    engine = create_engine(DATABASE_URL, pool_size=50, max_overflow=100, pool_timeout=10)
"""

_STANDARD_ONELINE = """if DATABASE_URL and "sqlite" in DATABASE_URL:
    engine = create_engine(
        DATABASE_URL, poolclass=NullPool, connect_args={"check_same_thread": False}
    )
else:
    engine = create_engine(DATABASE_URL, pool_size=50, max_overflow=100, pool_timeout=10)
"""

_REPLACEMENT_BLOCK = """

from database.db_config import get_db_engine

engine = get_db_engine()
"""


def _old_var_and_std_block(var_line: str) -> tuple[str, str]:
    """Return (old_var_line + existing_block, new_var_and_block)."""
    # Try with-comment version first
    with_comment = var_line + _STANDARD_SQLITE
    oneline = var_line + _STANDARD_ONELINE
    return (with_comment, oneline)


# Files with the standard comment-annotated block (most common)
for _fn in [
    "auth_db.py",
    "settings_db.py",
    "action_center_db.py",
    "analyzer_db.py",
    "chart_prefs_db.py",
    "chartink_db.py",
    "flow_db.py",
    "leverage_db.py",
    "qty_freeze_db.py",
    "strategy_db.py",
    "symbol.py",
]:
    _var = 'DATABASE_URL = os.getenv("DATABASE_URL")\n'
    _add(_fn, _var + _STANDARD_SQLITE, _var.rstrip() + _REPLACEMENT_BLOCK)
    _add(_fn, _var + _STANDARD_ONELINE, _var.rstrip() + _REPLACEMENT_BLOCK)

# strategy_portfolio_db.py — has CLAUDE.md comment
_add(
    "strategy_portfolio_db.py",
    'DATABASE_URL = os.getenv("DATABASE_URL")\n\nif DATABASE_URL and "sqlite" in DATABASE_URL:\n    # NullPool is the project-wide SQLite pattern (see CLAUDE.md).\n    engine = create_engine(\n        DATABASE_URL, poolclass=NullPool, connect_args={"check_same_thread": False}\n    )\nelse:\n    engine = create_engine(DATABASE_URL, pool_size=50, max_overflow=100, pool_timeout=10)\n',
    'DATABASE_URL = os.getenv("DATABASE_URL")\n\nfrom database.db_config import get_db_engine\n\nengine = get_db_engine()\n',
)

# symbol.py (apilog_db.py has the one-line block, already covered above with _STANDARD_ONELINE match)

# apilog_db.py
_add(
    "apilog_db.py",
    'DATABASE_URL = os.getenv("DATABASE_URL")  # Replace with your SQLite path\n\nif DATABASE_URL and "sqlite" in DATABASE_URL:\n    # SQLite: Use NullPool to prevent connection pool exhaustion\n    engine = create_engine(\n        DATABASE_URL, poolclass=NullPool, connect_args={"check_same_thread": False}\n    )\nelse:\n    # For other databases like PostgreSQL, use connection pooling\n    engine = create_engine(DATABASE_URL, pool_size=50, max_overflow=100, pool_timeout=10)\n',
    'DATABASE_URL = os.getenv("DATABASE_URL")  # Replace with your SQLite path\n\nfrom database.db_config import get_db_engine\n\nengine = get_db_engine()\n',
)

# user_db.py — has ``echo=False`` on both paths
_add(
    "user_db.py",
    'DATABASE_URL = os.getenv("DATABASE_URL")\n\n# Engine and session setup\n# Conditionally create engine based on DB type\nif DATABASE_URL and "sqlite" in DATABASE_URL:\n    # SQLite: Use NullPool to prevent connection pool exhaustion\n    engine = create_engine(\n        DATABASE_URL, echo=False, poolclass=NullPool, connect_args={"check_same_thread": False}\n    )\nelse:\n    # For other databases like PostgreSQL, use connection pooling\n    engine = create_engine(\n        DATABASE_URL, echo=False, pool_size=50, max_overflow=100, pool_timeout=10\n    )\n',
    'DATABASE_URL = os.getenv("DATABASE_URL")\n\nfrom database.db_config import get_db_engine\n\nengine = get_db_engine()\n',
)

# market_calendar_db.py — standard block
_add(
    "market_calendar_db.py",
    'DATABASE_URL = os.getenv("DATABASE_URL")\n\n# Conditionally create engine based on DB type\nif DATABASE_URL and "sqlite" in DATABASE_URL:\n    engine = create_engine(\n        DATABASE_URL, poolclass=NullPool, connect_args={"check_same_thread": False}\n    )\nelse:\n    engine = create_engine(DATABASE_URL, pool_size=50, max_overflow=100, pool_timeout=10)\n',
    'DATABASE_URL = os.getenv("DATABASE_URL")\n\nfrom database.db_config import get_db_engine\n\nengine = get_db_engine()\n',
)

# ============================ SPECIAL URL KEYS ============================

# traffic_db.py — LOGS_DATABASE_URL
_add(
    "traffic_db.py",
    'LOGS_DATABASE_URL = os.getenv("LOGS_DATABASE_URL", "sqlite:///db/logs.db")\n\n# Conditionally create engine based on DB type\nif LOGS_DATABASE_URL and "sqlite" in LOGS_DATABASE_URL:\n    # SQLite: Use NullPool — each checkout creates a fresh connection, and\n    # closing it returns the FD immediately.  Session cleanup (which prevents\n    # FD leaks) is handled by:\n    #   - app.py teardown_appcontext (removes all scoped sessions per request)\n    #   - traffic_logger.py (logs_session.remove() in finally block)\n    #   - security_middleware.py (logs_session.remove() for banned-IP path)\n    # StaticPool (single shared connection) must NOT be used here: concurrent\n    # requests on the same SQLite connection cause "bad parameter or other API\n    # misuse" and "cannot commit — SQL statements in progress" errors on all\n    # platforms (Windows, Mac, Linux).\n    logs_engine = create_engine(\n        LOGS_DATABASE_URL, poolclass=NullPool, connect_args={"check_same_thread": False}\n    )\nelse:\n    # For other databases like PostgreSQL, use connection pooling\n    logs_engine = create_engine(LOGS_DATABASE_URL, pool_size=50, max_overflow=100, pool_timeout=10)\n',
    'LOGS_DATABASE_URL = os.getenv("LOGS_DATABASE_URL", "sqlite:///db/logs.db")\n\nfrom database.db_config import get_db_engine\n\nlogs_engine = get_db_engine("LOGS_DATABASE_URL", "sqlite:///db/logs.db")\n',
)

# latency_db.py — LATENCY_DATABASE_URL
_add(
    "latency_db.py",
    'LATENCY_DATABASE_URL = os.getenv("LATENCY_DATABASE_URL", "sqlite:///db/latency.db")\n\n# Conditionally create engine based on DB type\nif LATENCY_DATABASE_URL and "sqlite" in LATENCY_DATABASE_URL:\n    # SQLite: Use NullPool to prevent connection pool exhaustion\n    latency_engine = create_engine(\n        LATENCY_DATABASE_URL, poolclass=NullPool, connect_args={"check_same_thread": False}\n    )\nelse:\n    # For other databases like PostgreSQL, use connection pooling\n    latency_engine = create_engine(\n        LATENCY_DATABASE_URL, pool_size=50, max_overflow=100, pool_timeout=10\n    )\n',
    'LATENCY_DATABASE_URL = os.getenv("LATENCY_DATABASE_URL", "sqlite:///db/latency.db")\n\nfrom database.db_config import get_db_engine\n\nlatency_engine = get_db_engine("LATENCY_DATABASE_URL", "sqlite:///db/latency.db")\n',
)

# health_db.py — HEALTH_DATABASE_URL
_add(
    "health_db.py",
    'HEALTH_DATABASE_URL = os.getenv("HEALTH_DATABASE_URL", "sqlite:///db/health.db")\n\n# Conditionally create engine based on DB type\nif HEALTH_DATABASE_URL and "sqlite" in HEALTH_DATABASE_URL:\n    # SQLite: Use NullPool to prevent connection pool exhaustion\n    health_engine = create_engine(\n        HEALTH_DATABASE_URL, poolclass=NullPool, connect_args={"check_same_thread": False}\n    )\nelse:\n    # For other databases like PostgreSQL, use connection pooling\n    health_engine = create_engine(\n        HEALTH_DATABASE_URL, pool_size=50, max_overflow=100, pool_timeout=10\n    )\n',
    'HEALTH_DATABASE_URL = os.getenv("HEALTH_DATABASE_URL", "sqlite:///db/health.db")\n\nfrom database.db_config import get_db_engine\n\nhealth_engine = get_db_engine("HEALTH_DATABASE_URL", "sqlite:///db/health.db")\n',
)

# sandbox_db.py — SANDBOX_DATABASE_URL with smaller pool (20/40)
_add(
    "sandbox_db.py",
    'SANDBOX_DATABASE_URL = os.getenv("SANDBOX_DATABASE_URL", "sqlite:///db/sandbox.db")\n\n# Conditionally create engine based on DB type\nif SANDBOX_DATABASE_URL and "sqlite" in SANDBOX_DATABASE_URL:\n    # SQLite: Use NullPool to prevent connection pool exhaustion\n    engine = create_engine(\n        SANDBOX_DATABASE_URL, poolclass=NullPool, connect_args={"check_same_thread": False}\n    )\nelse:\n    # For other databases like PostgreSQL, use connection pooling\n    engine = create_engine(SANDBOX_DATABASE_URL, pool_size=20, max_overflow=40, pool_timeout=10)\n',
    'SANDBOX_DATABASE_URL = os.getenv("SANDBOX_DATABASE_URL", "sqlite:///db/sandbox.db")\n\nfrom database.db_config import get_db_engine\n\nengine = get_db_engine("SANDBOX_DATABASE_URL", "sqlite:///db/sandbox.db", pool_size=20, max_overflow=40)\n',
)

# ============================ SPECIAL PATTERNS ============================

# master_contract_status_db.py — uses SessionLocal, echo=False, connect_args timeout
_add(
    "master_contract_status_db.py",
    'DB_PATH = os.getenv("DATABASE_URL", "sqlite:///db/silvertrade.db")\n\n# Ensure the directory exists\nos.makedirs(os.path.dirname(DB_PATH.replace("sqlite:///", "")), exist_ok=True)\n\n# Create the engine and session\n# Conditionally create engine based on DB type\nif DB_PATH and "sqlite" in DB_PATH:\n    # SQLite: Use NullPool to prevent connection pool exhaustion\n    engine = create_engine(\n        DB_PATH,\n        echo=False,\n        poolclass=NullPool,\n        connect_args={"check_same_thread": False, "timeout": 30},\n    )\nelse:\n    # For other databases like PostgreSQL, use connection pooling\n    engine = create_engine(DB_PATH, echo=False, pool_size=50, max_overflow=100, pool_timeout=10)\n',
    'DB_PATH = os.getenv("DATABASE_URL", "sqlite:///db/silvertrade.db")\n\n# Ensure the directory exists\nos.makedirs(os.path.dirname(DB_PATH.replace("sqlite:///", "")), exist_ok=True)\n\nfrom database.db_config import get_db_engine\n\nengine = get_db_engine("DATABASE_URL", "sqlite:///db/silvertrade.db")\n',
)

# telegram_db.py — different default URL, PG path has pool_pre_ping+pool_recycle
_add(
    "telegram_db.py",
    'DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///db/telegram.db")\nif DATABASE_URL.startswith("sqlite:///") and ":memory:" not in DATABASE_URL:\n    # Ensure the directory exists for file-based SQLite, but not for in-memory\n    db_path = DATABASE_URL.replace("sqlite:///", "")\n    if os.path.dirname(db_path):  # Only create if a directory is specified\n        os.makedirs(os.path.dirname(db_path), exist_ok=True)\n\n# Encryption setup for API keys\nTELEGRAM_KEY_SALT = os.getenv("TELEGRAM_KEY_SALT", "telegram-silvertrade-salt").encode()',
    'DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///db/telegram.db")\nif DATABASE_URL.startswith("sqlite:///") and ":memory:" not in DATABASE_URL:\n    db_path = DATABASE_URL.replace("sqlite:///", "")\n    if os.path.dirname(db_path):\n        os.makedirs(os.path.dirname(db_path), exist_ok=True)\n\nTELEGRAM_KEY_SALT = os.getenv("TELEGRAM_KEY_SALT", "telegram-silvertrade-salt").encode()',
)

# telegram_db.py — engine + session creation (separate block after encryption setup)
_add(
    "telegram_db.py",
    '\n# Create engine and session\n# Conditionally create engine based on DB type\nif DATABASE_URL and "sqlite" in DATABASE_URL:\n    # SQLite: Use NullPool to prevent connection pool exhaustion\n    engine = create_engine(\n        DATABASE_URL, poolclass=NullPool, connect_args={"check_same_thread": False}\n    )\nelse:\n    # For other databases like PostgreSQL, use connection pooling\n    engine = create_engine(\n        DATABASE_URL, pool_pre_ping=True, pool_recycle=3600, pool_size=50, max_overflow=100\n    )',
    '\nfrom database.db_config import get_db_engine\n\nengine = get_db_engine("DATABASE_URL", "sqlite:///db/telegram.db")',
)


# ============================ HELPER: clean up orphaned imports =====================


def _clean_imports(content: str) -> str:
    """Remove ``create_engine`` / ``NullPool`` imports no longer needed."""
    lines = content.split("\n")
    keep = []
    for line in lines:
        # Remove ``from sqlalchemy import … create_engine …``
        if re.match(r"^\s*from\s+sqlalchemy\s+import", line) and "create_engine" in line:
            # Remove just ``create_engine, `` or ``, create_engine`` from the import
            cleaned = re.sub(r",?\s*create_engine\s*,?\s*", ", ", line)
            cleaned = cleaned.rstrip(", ")
            if cleaned.strip().rstrip(",") in (
                "from sqlalchemy import",
                "from sqlalchemy import ,",
                "from sqlalchemy import  ,",
            ):
                continue  # nothing left on this line
            keep.append(cleaned)
            continue
        # Remove ``from sqlalchemy.pool import NullPool``
        if re.match(r"^\s*from\s+sqlalchemy\.pool\s+import\s+NullPool\s*$", line):
            continue
        keep.append(line)
    return "\n".join(keep)


# ============================ MAIN ============================


def main():
    modified = 0
    skipped = 0

    for path, old, new, _ in REPLACEMENTS:
        if not os.path.exists(path):
            print(f"  SKIP  {os.path.basename(path)} — file not found")
            skipped += 1
            continue

        with open(path) as f:
            content = f.read()

        # Skip files that already use get_db_engine
        if "from database.db_config import get_db_engine" in content or "from database.db_config import create_db_engine" in content:
            print(f"  SKIP  {os.path.basename(path)} — already uses db_config")
            skipped += 1
            continue

        if old not in content:
            print(f"  SKIP  {os.path.basename(path)} — old block not found")
            skipped += 1
            continue

        content = content.replace(old, new, 1)
        content = _clean_imports(content)

        with open(path, "w") as f:
            f.write(content)

        print(f"  OK    {os.path.basename(path)}")
        modified += 1

    # Now fix organization_db.py — it already imports create_db_engine
    # but also creates local sessions per function. Just update the import
    # to use get_db_engine and remove sqlalchemy create_engine import.
    org_path = os.path.join(PROJECT, "database", "organization_db.py")
    with open(org_path) as f:
        content = f.read()

    needs_org_fix = False
    if "from sqlalchemy import" in content and "create_engine" in content:
        # Replace the sqlalchemy import to remove create_engine
        content = content.replace(
            "from sqlalchemy import (\n    Boolean, Column, DateTime, ForeignKey, Integer, String, Text,\n    create_engine, UniqueConstraint,\n)",
            "from sqlalchemy import (\n    Boolean, Column, DateTime, ForeignKey, Integer, String, Text,\n    UniqueConstraint,\n)"
        )
        needs_org_fix = True

    if "from database.db_config import create_db_engine" in content:
        content = content.replace(
            "from database.db_config import create_db_engine",
            "from database.db_config import get_db_engine"
        )
        content = content.replace(
            "engine = create_db_engine(",
            "engine = get_db_engine("
        )
        needs_org_fix = True

    if needs_org_fix:
        with open(org_path, "w") as f:
            f.write(content)
        print(f"  OK    organization_db.py")

    print(f"\n{'='*40}")
    print(f"  Modified: {modified}")
    print(f"  Skipped:  {skipped}")
    print(f"{'='*40}")


if __name__ == "__main__":
    main()
