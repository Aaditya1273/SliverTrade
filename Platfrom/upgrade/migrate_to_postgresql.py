#!/usr/bin/env python3
"""
╔══════════════════════════════════════════════════════════════════════╗
║  SilverTrade AI — SQLite → PostgreSQL Migration Script              ║
║                                                                      ║
║  Reads ALL existing SQLite databases and migrates every table,       ║
║  row, index, constraint, and sequence to Supabase PostgreSQL.       ║
║                                                                      ║
║  Usage:                                                              ║
║    1. Set DATABASE_URL et al. in .env to point at Supabase          ║
║    2. uv run python upgrade/migrate_to_postgresql.py --dry-run      ║
║    3. uv run python upgrade/migrate_to_postgresql.py                ║
║                                                                      ║
║  Database mapping:                                                   ║
║    sqlite:///db/silvertrade.db  →  DATABASE_URL (public schema)     ║
║    sqlite:///db/logs.db         →  LOGS_DATABASE_URL (logs schema)  ║
║    sqlite:///db/latency.db      →  LATENCY_DATABASE_URL             ║
║    sqlite:///db/health.db       →  HEALTH_DATABASE_URL              ║
║    sqlite:///db/sandbox.db      →  SANDBOX_DATABASE_URL             ║
╚══════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import time
import argparse
import textwrap
from datetime import datetime
from pathlib import Path
from urllib.parse import quote, urlparse

# ── Project root ────────────────────────────────────────────────
PROJECT_ROOT = Path(__file__).resolve().parent.parent


def load_env():
    """Load .env file to get database URLs."""
    env_path = PROJECT_ROOT / ".env"
    if not env_path.exists():
        print("❌ .env file not found at", env_path)
        print("   Create one from .sample.env first")
        sys.exit(1)

    # Simple .env parser (no external deps)
    with open(env_path) as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#"):
                continue
            if "=" not in line:
                continue
            key, _, value = line.partition("=")
            key = key.strip()
            value = value.strip().strip("'\"").strip()
            os.environ.setdefault(key, value)


def normalize_pg_url(db_url):
    """Normalize a PostgreSQL URL for use with psycopg2.connect().

    Handles:
      1. Strips SQLAlchemy-specific driver suffix (``+psycopg2``),
         because raw ``psycopg2.connect()`` doesn't recognise it.
      2. Strips the ``?options=...`` query parameter — libpq in some
         environments rejects ``options`` as a URI query parameter.
         The caller should set ``search_path`` via ``SET search_path TO``
         after connecting instead.
      3. Does NOT re-encode the password — the .env already contains
         a properly URL-encoded password (e.g. ``%21`` for ``!``).
    """
    if not db_url:
        return db_url

    # Strip SQLAlchemy driver suffix
    url = db_url.replace("postgresql+psycopg2://", "postgresql://")
    url = url.replace("postgres+psycopg2://", "postgres://")

    # Strip ?options=... parameter (psycopg2/libpq doesn't accept it in URI form)
    if "?options=" in url:
        url = url.split("?options=")[0]

    return url


def get_table_list_sqlite(conn):
    """Get all user tables from SQLite database."""
    cursor = conn.execute(
        "SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%' "
        "ORDER BY name"
    )
    return [row[0] for row in cursor.fetchall()]


def get_table_schema_sqlite(conn, table_name):
    """Get column definitions for a SQLite table."""
    cursor = conn.execute(f'PRAGMA table_info("{table_name}")')
    columns = []
    for row in cursor.fetchall():
        columns.append(
            {
                "cid": row[0],
                "name": row[1],
                "type": row[2],
                "notnull": bool(row[3]),
                "dflt_value": row[4],
                "pk": bool(row[5]),
            }
        )
    return columns


def get_table_indexes_sqlite(conn, table_name):
    """Get index definitions for a SQLite table."""
    cursor = conn.execute(f'PRAGMA index_list("{table_name}")')
    indexes = []
    for row in cursor.fetchall():
        idx_name = row[1]
        unique = bool(row[2])
        # Get index columns
        col_cursor = conn.execute(f'PRAGMA index_info("{idx_name}")')
        columns = [col_row[2] for col_row in col_cursor.fetchall()]
        indexes.append(
            {
                "name": idx_name,
                "unique": unique,
                "columns": columns,
            }
        )
    return indexes


def generate_create_table_sql(table_name, columns, indexes):
    """Generate PostgreSQL CREATE TABLE statement from SQLite schema."""
    col_defs = []
    for col in columns:
        pg_type = sqlite_to_postgres_type(col["type"])
        col_def = f"    {col['name']} {pg_type}"

        if col["pk"]:
            col_def += " PRIMARY KEY"
        if col["notnull"] and not col["pk"]:
            col_def += " NOT NULL"
        if col["dflt_value"] is not None:
            default = col["dflt_value"]
            if default.upper() == "CURRENT_TIMESTAMP":
                col_def += " DEFAULT CURRENT_TIMESTAMP"
            elif default.upper().startswith("'") and default.upper().endswith("'"):
                col_def += f" DEFAULT {default}"
            else:
                col_def += f" DEFAULT {default}"
        col_defs.append(col_def)

    sql = f"CREATE TABLE IF NOT EXISTS {table_name} (\n"
    sql += ",\n".join(col_defs)
    sql += "\n)"

    return sql


def sqlite_to_postgres_type(sqlite_type):
    """Map SQLite types to PostgreSQL types."""
    t = sqlite_type.upper()
    if "INT" in t:
        return "INTEGER"
    elif "CHAR" in t or "TEXT" in t or "CLOB" in t:
        return "TEXT"
    elif "BLOB" in t:
        return "BYTEA"
    elif "REAL" in t or "FLOAT" in t or "DOUBLE" in t:
        return "DOUBLE PRECISION"
    elif "DECIMAL" in t or "NUMERIC" in t:
        # Parse precision if available
        if "(" in t:
            return t.upper()
        return "NUMERIC"
    elif "BOOLEAN" in t:
        return "BOOLEAN"
    elif "DATE" in t:
        return "TIMESTAMP" if "TIME" in t else "DATE"
    elif "JSON" in t:
        return "JSONB"
    else:
        return "TEXT"


def fix_sqlite_defaults_for_pg(sql, table_name, columns):
    """Fix SQLite-specific default values for PostgreSQL."""
    # SQLite uses 0/1 for booleans - add explicit cast
    for col in columns:
        t = col["type"].upper()
        if "BOOLEAN" in t and col["dflt_value"] in ("0", "1"):
            replacement = f"DEFAULT {col['dflt_value']}"
            pg_replacement = f"DEFAULT {'TRUE' if col['dflt_value'] == '1' else 'FALSE'}"
            sql = sql.replace(replacement, pg_replacement)

    # SQLite allows ``func.now()`` as default - fix for PG
    if "CURRENT_TIMESTAMP" in sql and "DEFAULT CURRENT_TIMESTAMP" not in sql:
        sql = sql.replace("now()", "CURRENT_TIMESTAMP")

    return sql


# ── Database configurations ─────────────────────────────────────
# SQLite paths are determined directly from known project paths,
# NOT from env vars — because by the time migration runs, the user
# has already updated DATABASE_URL et al. to point at PostgreSQL.
DATABASE_CONFIGS = [
    {
        "name": "Main Database",
        # Prefer legacy openalgo.db; fall back to silvertrade.db for fresh installs
        "sqlite_relative": "db/openalgo.db",
        "alt_sqlite_relative": "db/silvertrade.db",
        "pg_url_key": "DATABASE_URL",
        "schema": "public",
        "description": "auth, users, settings, strategies, symbols, telegram, flow, etc.",
    },
    {
        "name": "Logs Database (Traffic)",
        "sqlite_relative": "db/logs.db",
        "pg_url_key": "LOGS_DATABASE_URL",
        "schema": "logs",
        "description": "traffic_logs, ip_bans, error_404_tracker, invalid_api_key_tracker",
    },
    {
        "name": "Latency Database",
        "sqlite_relative": "db/latency.db",
        "pg_url_key": "LATENCY_DATABASE_URL",
        "schema": "latency",
        "description": "order_latency logs",
    },
    {
        "name": "Health Database",
        "sqlite_relative": "db/health.db",
        "pg_url_key": "HEALTH_DATABASE_URL",
        "schema": "health",
        "description": "health_metrics, health_alerts",
    },
    {
        "name": "Sandbox Database",
        "sqlite_relative": "db/sandbox.db",
        "pg_url_key": "SANDBOX_DATABASE_URL",
        "schema": "sandbox",
        "description": "sandbox_orders, sandbox_trades, sandbox_positions, sandbox_funds, etc.",
    },
]


def migrate_database(config, dry_run=False, force=False):
    """Migrate a single database from SQLite to PostgreSQL."""
    name = config["name"]
    pg_url = os.getenv(config["pg_url_key"], "")

    # SQLite path supports a fallback via "alt_sqlite_relative"
    sqlite_path = PROJECT_ROOT / config["sqlite_relative"]

    # If the primary SQLite path doesn't exist, try the alternate
    alt_sqlite_relative = config.get("alt_sqlite_relative")
    if not sqlite_path.exists() and alt_sqlite_relative:
        alt_path = PROJECT_ROOT / alt_sqlite_relative
        if alt_path.exists():
            print(f"  ℹ️  Primary SQLite not found at {config['sqlite_relative']}")
            print(f"     Using alternate: {alt_sqlite_relative}")
            sqlite_path = alt_path

    if not sqlite_path.exists():
        print(f"  ⏭️  {name}: SQLite database not found at {sqlite_path}, skipping")
        return {"status": "skipped", "reason": "sqlite_not_found"}

    if not pg_url:
        print(f"  ❌ {name}: PostgreSQL URL not set ({config['pg_url_key']})")
        return {"status": "failed", "reason": "pg_url_not_set"}

    # Normalize URL for psycopg2 (strip driver suffix, preserve already-encoded password)
    pg_url = normalize_pg_url(pg_url)

    print(f"\n{'=' * 70}")
    print(f"  📦 {name}")
    print(f"  📄 SQLite:    {sqlite_path}")
    print(f"  🐘 PostgreSQL: {config['pg_url_key']}")
    print(f"  📋 Schema:    {config['schema']}")
    print(f"  📝 Tables:    {config['description']}")
    print(f"{'=' * 70}")

    # ── Connect to SQLite ──────────────────────────────────────
    try:
        import sqlite3

        sqlite_conn = sqlite3.connect(str(sqlite_path))
        sqlite_conn.row_factory = sqlite3.Row
    except Exception as e:
        print(f"  ❌ Failed to connect to SQLite: {e}")
        return {"status": "failed", "error": str(e)}

    # ── Get all tables ─────────────────────────────────────────
    try:
        tables = get_table_list_sqlite(sqlite_conn)
    except Exception as e:
        print(f"  ❌ Failed to read tables from SQLite database: {e}")
        print(f"     The database may be corrupted. Creating fresh schema in PostgreSQL.")
        sqlite_conn.close()
        # Return a special status so the caller knows to create tables but skip data migration
        return {"status": "corrupted", "error": str(e), "schema": config["schema"]}

    if not tables:
        print(f"  ⏭️  No tables found in SQLite database")
        sqlite_conn.close()
        return {"status": "skipped", "reason": "no_tables"}

    print(f"  Found {len(tables)} tables: {', '.join(tables)}")

    # ── Connect to PostgreSQL ──────────────────────────────────
    if not dry_run:
        try:
            import psycopg2

            pg_conn = psycopg2.connect(pg_url)
            pg_conn.autocommit = False
            pg_cur = pg_conn.cursor()

            # Create schema if not exists
            schema = config["schema"]
            pg_cur.execute(f"CREATE SCHEMA IF NOT EXISTS {schema}")
            pg_conn.commit()

            # Set search_path for schema-isolated databases (logs, latency, health, sandbox)
            # This ensures unqualified table references land in the correct schema
            if schema != "public":
                pg_cur.execute(f"SET search_path TO {schema}")
                pg_conn.commit()

        except Exception as e:
            print(f"  ❌ Failed to connect to PostgreSQL: {e}")
            sqlite_conn.close()
            return {"status": "failed", "error": str(e)}

    migrated_tables = []
    total_rows = 0
    errors = []

    for table_name in tables:
        try:
            # Get schema
            columns = get_table_schema_sqlite(sqlite_conn, table_name)
            indexes = get_table_indexes_sqlite(sqlite_conn, table_name)

            # Generate CREATE TABLE SQL
            qualified_name = (
                f"{config['schema']}.{table_name}" if config["schema"] != "public" else table_name
            )
            create_sql = generate_create_table_sql(qualified_name, columns, indexes)
            create_sql = fix_sqlite_defaults_for_pg(create_sql, table_name, columns)

            # ── Dry run ────────────────────────────────────────
            if dry_run:
                print(f"\n  📋 Table: {table_name}")
                print(f"     Columns: {len(columns)}")
                print(f"     Indexes: {len(indexes)}")
                continue

            # ── Create table ───────────────────────────────────
            try:
                pg_cur.execute(create_sql)
                pg_conn.commit()
            except Exception as e:
                if "already exists" in str(e).lower() and not force:
                    print(
                        f"     ⚠️  Table {table_name} already exists, skipping (use --force to recreate)"
                    )
                    errors.append(f"{table_name}: already exists")
                    continue
                elif "already exists" in str(e).lower() and force:
                    print(f"     ⚠️  Dropping and recreating {table_name} (--force)...")
                    pg_cur.execute(f"DROP TABLE IF EXISTS {qualified_name} CASCADE")
                    pg_cur.execute(create_sql)
                    pg_conn.commit()

            # ── Count rows in SQLite ───────────────────────────
            count_cursor = sqlite_conn.execute(f'SELECT COUNT(*) FROM "{table_name}"')
            row_count = count_cursor.fetchone()[0]

            if row_count == 0:
                print(f"     ✅ {table_name}: 0 rows (empty table created)")
                migrated_tables.append(table_name)
                continue

            # ── Fetch all data from SQLite ─────────────────────
            data_cursor = sqlite_conn.execute(f'SELECT * FROM "{table_name}"')
            rows = data_cursor.fetchall()
            col_names = [desc[0] for desc in data_cursor.description]

            # ── Insert into PostgreSQL ─────────────────────────
            placeholders = ", ".join(["%s"] * len(col_names))
            columns_str = ", ".join(col_names)
            insert_sql = f"INSERT INTO {qualified_name} ({columns_str}) VALUES ({placeholders})"

            # Batch insert for performance
            batch_size = 500
            inserted = 0
            for i in range(0, len(rows), batch_size):
                batch = rows[i : i + batch_size]
                batch_values = []
                for row in batch:
                    values = []
                    for val in row:
                        if isinstance(val, bytes):
                            values.append(psycopg2.Binary(val))
                        if isinstance(val, str) and len(val) > 0:
                            # Check if it's a JSON string
                            # SQLite stores JSON as TEXT — PostgreSQL JSONB accepts valid
                            # JSON strings directly. No need to parse and re-serialize.
                            if val.strip().startswith(("{", "[")):
                                # Pass through as-is: SQLite's TEXT is already valid JSON
                                values.append(val)
                            else:
                                values.append(val)
                        else:
                            values.append(val)
                    batch_values.append(values)

                try:
                    pg_cur.executemany(insert_sql, batch_values)
                    pg_conn.commit()
                    inserted += len(batch)
                    print(f"     📊 {table_name}: {inserted}/{row_count} rows...", end="\r")
                except Exception as batch_e:
                    pg_conn.rollback()
                    # Fall back to row-by-row (handles problematic data)
                    print(f"\n     ⚠️  Batch insert failed, falling back to row-by-row: {batch_e}")
                    for values in batch_values:
                        try:
                            pg_cur.execute(insert_sql, values)
                            pg_conn.commit()
                            inserted += 1
                        except Exception as row_e:
                            pg_conn.rollback()
                            print(f"     ⚠️  Row insert failed (skipping): {row_e}")

            print(f"     ✅ {table_name}: {inserted} rows migrated")
            migrated_tables.append(table_name)
            total_rows += inserted

            # ── Create indexes ─────────────────────────────────
            for idx in indexes:
                idx_name = idx["name"]
                # Skip auto-generated indexes (PRIMARY KEY, UNIQUE)
                if idx_name.startswith("sqlite_autoindex"):
                    continue

                idx_columns = ", ".join(idx["columns"])
                unique_clause = "UNIQUE " if idx["unique"] else ""
                idx_sql = f"CREATE {unique_clause}INDEX IF NOT EXISTS {idx_name} ON {qualified_name} ({idx_columns})"

                try:
                    pg_cur.execute(idx_sql)
                    pg_conn.commit()
                except Exception as idx_e:
                    print(f"     ⚠️  Index {idx_name} failed: {idx_e}")
                    pg_conn.rollback()

        except Exception as e:
            print(f"     ❌ Error migrating {table_name}: {e}")
            errors.append(f"{table_name}: {str(e)}")
            if not dry_run:
                pg_conn.rollback()

    # ── Cleanup ─────────────────────────────────────────────────
    sqlite_conn.close()
    if not dry_run:
        pg_cur.close()
        pg_conn.close()

    return {
        "status": "completed" if not errors else "partial",
        "tables_migrated": migrated_tables,
        "total_rows": total_rows,
        "errors": errors,
    }


def main():
    parser = argparse.ArgumentParser(
        description="Migrate SilverTrade AI from SQLite to PostgreSQL (Supabase)",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=textwrap.dedent("""\
            Examples:
              # Dry run (see what will happen without making changes)
              uv run python upgrade/migrate_to_postgresql.py --dry-run

              # Full migration
              uv run python upgrade/migrate_to_postgresql.py

              # Force recreate tables (drops existing data!)
              uv run python upgrade/migrate_to_postgresql.py --force

              # Migrate only specific database
              uv run python upgrade/migrate_to_postgresql.py --only main
              uv run python upgrade/migrate_to_postgresql.py --only sandbox
        """),
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Preview what will be migrated without making changes",
    )
    parser.add_argument(
        "--force",
        action="store_true",
        help="Drop and recreate tables if they already exist in PostgreSQL",
    )
    parser.add_argument(
        "--only",
        choices=["main", "logs", "latency", "health", "sandbox", "all"],
        default="all",
        help="Migrate only a specific database",
    )
    parser.add_argument(
        "--set-env",
        action="store_true",
        help="Automatically update .env with Supabase PostgreSQL URLs for all 5 databases",
    )

    args = parser.parse_args()

    # ── Banner ──────────────────────────────────────────────────
    print("""
╔═══════════════════════════════════════════════════════════════╗
║   SilverTrade AI — SQLite → PostgreSQL Migration             ║
║   Target: Supabase PostgreSQL 17.6                           ║
╚═══════════════════════════════════════════════════════════════╝
""")

    # Load environment
    load_env()

    if args.dry_run:
        print("🔍 DRY RUN MODE — No changes will be made\n")

    # Filter databases
    configs = DATABASE_CONFIGS
    if args.only != "all":
        config_map = {
            "main": DATABASE_CONFIGS[0],
            "logs": DATABASE_CONFIGS[1],
            "latency": DATABASE_CONFIGS[2],
            "health": DATABASE_CONFIGS[3],
            "sandbox": DATABASE_CONFIGS[4],
        }
        configs = [config_map[args.only]]

    # ── Set environment variables in .env ─────────────────────
    if args.set_env:
        print("\n📝 Updating .env with Supabase PostgreSQL URLs...")

        # Read current .env
        env_path = PROJECT_ROOT / ".env"
        with open(env_path) as f:
            env_content = f.read()

        # Check if Supabase URL is already set
        supabase_url = os.getenv("DATABASE_URL")
        if not supabase_url or "supabase" not in supabase_url:
            print("""
❌ DATABASE_URL is not set to Supabase in your .env file!

   Please add the following to your .env file:
     DATABASE_URL = 'postgresql://postgres.YOUR_REF:YOUR_PASSWORD@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres'
     LOGS_DATABASE_URL = 'postgresql://postgres.YOUR_REF:YOUR_PASSWORD@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres?options=-c%20search_path=logs'
     LATENCY_DATABASE_URL = 'postgresql://postgres.YOUR_REF:YOUR_PASSWORD@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres?options=-c%20search_path=latency'
     HEALTH_DATABASE_URL = 'postgresql://postgres.YOUR_REF:YOUR_PASSWORD@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres?options=-c%20search_path=health'
     SANDBOX_DATABASE_URL = 'postgresql://postgres.YOUR_REF:YOUR_PASSWORD@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres?options=-c%20search_path=sandbox'

   Note: The password contains special characters (!@#) that must be URL-encoded:
         ! → %21   @ → %40   # → %23
         Example: rawat_%21%40%23123
""")
            sys.exit(1)

        print(
            "   ✅ DATABASE_URL is set. Please also set LOGS_DATABASE_URL, LATENCY_DATABASE_URL, etc."
        )
        if not args.dry_run:
            return

    # ── Migration Summary ──────────────────────────────────────
    results = []
    start_time = time.time()

    for config in configs:
        result = migrate_database(config, dry_run=args.dry_run, force=args.force)
        results.append({config["name"]: result})

    elapsed = time.time() - start_time

    # ── Final Report ───────────────────────────────────────────
    print(f"\n{'=' * 70}")
    print("  📊 MIGRATION SUMMARY")
    print(f"{'=' * 70}")

    total_tables = 0
    total_rows = 0
    total_errors = 0
    skipped = 0

    for result in results:
        for db_name, db_result in result.items():
            status = db_result.get("status", "unknown")
            if status == "completed":
                tables = db_result.get("tables_migrated", [])
                rows = db_result.get("total_rows", 0)
                total_tables += len(tables)
                total_rows += rows
                print(f"  ✅ {db_name}: {len(tables)} tables, {rows} rows")
            elif status == "partial":
                tables = db_result.get("tables_migrated", [])
                rows = db_result.get("total_rows", 0)
                errs = db_result.get("errors", [])
                total_tables += len(tables)
                total_rows += rows
                total_errors += len(errs)
                print(f"  ⚠️  {db_name}: {len(tables)} tables, {rows} rows, {len(errs)} errors")
                for err in errs:
                    print(f"       ❌ {err}")
            elif status == "skipped":
                skipped += 1
                print(f"  ⏭️  {db_name}: {db_result.get('reason', 'skipped')}")
            elif status == "corrupted":
                # Database is corrupted — schema will be created fresh when app starts
                print(f"  💔 {db_name}: Corrupted (no data to migrate)")
                print(f"       PostgreSQL schemas ready. App will create fresh tables on startup.")
            else:
                print(f"  ❌ {db_name}: FAILED — {db_result.get('error', 'unknown')}")

    print(f"\n  ⏱️  Time: {elapsed:.1f}s")
    if not args.dry_run and total_tables > 0:
        print(f"\n  🎉 Successfully migrated {total_tables} tables with {total_rows} rows!")
    elif not args.dry_run and total_tables == 0:
        print(f"\n  ⚠️  No tables were migrated. Check errors above.")
    if total_errors:
        print(f"  ⚠️  {total_errors} errors occurred during migration (see details above)")
    if skipped:
        print(f"  ⏭️  {skipped} databases were skipped")

    if args.dry_run:
        print(f"\n  🔍 Dry run complete. Run without --dry-run to perform migration.")
    else:
        print(f"\n  📋 Next steps:")
        print(
            f"     1. Verify data: ./Platfrom/.venv/bin/python3 -c \"import psycopg2; c = psycopg2.connect(os.environ['DATABASE_URL']); c.cursor().execute('SELECT count(*) FROM auth'); print(c.fetchone())\""
        )
        print(f"     2. Update .env to use PostgreSQL URLs")
        print(f"     3. Start the application: uv run python app.py")
        print(f"     4. Monitor logs for any database errors")


if __name__ == "__main__":
    main()
