"""
SilverTrade AI — Signal Persistence Database
==============================================
SQLite-backed storage for trading signals, backtest results, accuracy
tracking, and alert rules.

Ensures signals survive Strategy Engine restarts and enables paginated
querying, filtering, and outcome tracking.

Tables:
  - signals:        Generated trading signals with full metadata
  - backtest_results: Backtest configuration + metrics
  - alert_rules:     User-defined alert preferences
  - outcome_tracker: Schedule for signal outcome evaluations
"""

import json
import logging
import os
import sqlite3
import threading
import time
from contextlib import contextmanager
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)

DB_DIR = os.path.join(os.path.dirname(__file__), "data")
DB_PATH = os.path.join(DB_DIR, "strategies.db")
_RETRY_DELAY = 0.05  # 50ms
_MAX_RETRIES = 5

_local = threading.local()


def _get_connection() -> sqlite3.Connection:
    """Get a thread-local database connection."""
    if not hasattr(_local, "conn") or _local.conn is None:
        os.makedirs(DB_DIR, exist_ok=True)
        _local.conn = sqlite3.connect(DB_PATH, timeout=10)
        _local.conn.row_factory = sqlite3.Row
        _local.conn.execute("PRAGMA journal_mode=WAL")
        _local.conn.execute("PRAGMA busy_timeout=5000")
    return _local.conn


@contextmanager
def _db_cursor():
    """Context manager for DB operations with automatic retry."""
    conn = _get_connection()
    for attempt in range(_MAX_RETRIES):
        try:
            yield conn.cursor()
            conn.commit()
            return
        except sqlite3.OperationalError as e:
            if "database is locked" in str(e) and attempt < _MAX_RETRIES - 1:
                time.sleep(_RETRY_DELAY * (attempt + 1))
                continue
            logger.error("Database error after %d retries: %s", attempt + 1, e)
            conn.rollback()
            raise
        except Exception:
            conn.rollback()
            raise


def init_db() -> None:
    """Create tables if they don't exist. Called once at startup."""
    with _db_cursor() as cur:
        cur.execute("""
            CREATE TABLE IF NOT EXISTS signals (
                id              TEXT PRIMARY KEY,
                symbol          TEXT NOT NULL,
                exchange        TEXT DEFAULT 'CRYPTO',
                decision        TEXT NOT NULL,
                confidence      REAL NOT NULL DEFAULT 0,
                price           REAL NOT NULL DEFAULT 0,
                reasoning       TEXT DEFAULT '',
                indicators      TEXT DEFAULT '{}',
                model_breakdown TEXT DEFAULT '{}',
                mock_data       INTEGER DEFAULT 0,
                executed        INTEGER DEFAULT 0,
                order_id        TEXT DEFAULT '',
                outcome_price   REAL,
                outcome_pct     REAL,
                was_correct     INTEGER,
                missed_profit_pct REAL,
                evaluated_at    TEXT,
                timestamp       TEXT NOT NULL,
                created_at      TEXT DEFAULT (datetime('now'))
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS backtest_results (
                id              INTEGER PRIMARY KEY AUTOINCREMENT,
                symbol          TEXT NOT NULL,
                exchange        TEXT DEFAULT 'CRYPTO',
                interval        TEXT DEFAULT '15m',
                start_date      TEXT,
                end_date        TEXT,
                initial_capital REAL DEFAULT 100000,
                win_rate        REAL DEFAULT 0,
                total_pnl       REAL DEFAULT 0,
                total_pnl_pct   REAL DEFAULT 0,
                max_drawdown    REAL DEFAULT 0,
                sharpe_ratio    REAL DEFAULT 0,
                profit_factor   REAL DEFAULT 0,
                calmar_ratio    REAL DEFAULT 0,
                total_trades    INTEGER DEFAULT 0,
                config          TEXT DEFAULT '{}',
                equity_curve    TEXT DEFAULT '[]',
                created_at      TEXT DEFAULT (datetime('now'))
            )
        """)

        cur.execute("""
            CREATE TABLE IF NOT EXISTS outcome_pending (
                signal_id       TEXT PRIMARY KEY,
                symbol          TEXT NOT NULL,
                exchange        TEXT DEFAULT 'CRYPTO',
                decision        TEXT NOT NULL,
                entry_price     REAL NOT NULL,
                signal_time     TEXT NOT NULL,
                retry_count     INTEGER DEFAULT 0,
                next_check_at   TEXT,
                created_at      TEXT DEFAULT (datetime('now'))
            )
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_signals_timestamp ON signals(timestamp DESC)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_signals_executed ON signals(executed)
        """)
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_outcome_pending_next_check ON outcome_pending(next_check_at)
        """)

    logger.info("Signal database initialised at %s", DB_PATH)


# ── Signals ──────────────────────────────────────────────────────────

def insert_signal(signal: Dict[str, Any]) -> str:
    """Insert a signal into the database. Returns the signal ID."""
    signal_id = signal.get("id", "")
    if not signal_id:
        import uuid
        signal_id = str(uuid.uuid4())[:8]

    timestamp = signal.get("timestamp", datetime.now(timezone.utc).isoformat())

    with _db_cursor() as cur:
        cur.execute("""
            INSERT OR REPLACE INTO signals
                (id, symbol, exchange, decision, confidence, price, reasoning,
                 indicators, model_breakdown, mock_data, executed, timestamp)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            signal_id,
            signal.get("symbol", ""),
            signal.get("exchange", "CRYPTO"),
            signal.get("decision", "HOLD"),
            signal.get("confidence", 0),
            signal.get("price", 0),
            signal.get("reasoning", ""),
            json.dumps(signal.get("indicators", {})),
            json.dumps(signal.get("model_breakdown", {})),
            1 if signal.get("mock_data") else 0,
            1 if signal.get("executed") else 0,
            timestamp,
        ))

    return signal_id


def get_signals(limit: int = 50, offset: int = 0) -> List[Dict[str, Any]]:
    """Fetch recent signals with pagination."""
    with _db_cursor() as cur:
        cur.execute("""
            SELECT * FROM signals ORDER BY timestamp DESC LIMIT ? OFFSET ?
        """, (limit, offset))
        rows = cur.fetchall()

    results = []
    for row in rows:
        d = dict(row)
        d["indicators"] = json.loads(d.get("indicators", "{}"))
        d["model_breakdown"] = json.loads(d.get("model_breakdown", "{}"))
        d["mock_data"] = bool(d.get("mock_data"))
        d["executed"] = bool(d.get("executed"))
        d["was_correct"] = bool(d["was_correct"]) if d["was_correct"] is not None else None
        results.append(d)
    return results


def get_signal_by_id(signal_id: str) -> Optional[Dict[str, Any]]:
    """Fetch a single signal by ID."""
    with _db_cursor() as cur:
        cur.execute("SELECT * FROM signals WHERE id = ?", (signal_id,))
        row = cur.fetchone()
    if not row:
        return None
    d = dict(row)
    d["indicators"] = json.loads(d.get("indicators", "{}"))
    d["model_breakdown"] = json.loads(d.get("model_breakdown", "{}"))
    return d


def mark_signal_executed(signal_id: str, order_id: str = "") -> None:
    """Mark a signal as executed (user placed an order for it)."""
    with _db_cursor() as cur:
        cur.execute("UPDATE signals SET executed = 1, order_id = ? WHERE id = ?", (order_id, signal_id))


def update_signal_outcome(signal_id: str, outcome_price: float, outcome_pct: float,
                          was_correct: bool, missed_profit_pct: float = 0) -> None:
    """Record the outcome of a signal after evaluation period."""
    with _db_cursor() as cur:
        cur.execute("""
            UPDATE signals SET
                outcome_price = ?, outcome_pct = ?, was_correct = ?,
                missed_profit_pct = ?, evaluated_at = datetime('now')
            WHERE id = ?
        """, (outcome_price, outcome_pct, int(was_correct), missed_profit_pct, signal_id))


def get_outcome_summary() -> Dict[str, Any]:
    """Aggregate signal accuracy statistics."""
    with _db_cursor() as cur:
        cur.execute("""
            SELECT
                COUNT(*) as total_evaluated,
                SUM(CASE WHEN was_correct = 1 THEN 1 ELSE 0 END) as correct,
                SUM(CASE WHEN was_correct = 0 THEN 1 ELSE 0 END) as incorrect,
                AVG(CASE WHEN was_correct = 1 THEN confidence ELSE NULL END) as avg_confidence_win
            FROM signals
            WHERE evaluated_at IS NOT NULL
        """)
        row = cur.fetchone()

        cur.execute("""
            SELECT decision, COUNT(*) as cnt, SUM(was_correct) as wins
            FROM signals
            WHERE evaluated_at IS NOT NULL
            GROUP BY decision
        """)
        by_decision = {r["decision"]: {"total": r["cnt"], "wins": r["wins"] or 0} for r in cur.fetchall()}

        cur.execute("""
            SELECT symbol, COUNT(*) as cnt, SUM(was_correct) as wins
            FROM signals
            WHERE evaluated_at IS NOT NULL
            GROUP BY symbol
            ORDER BY cnt DESC LIMIT 10
        """)
        by_symbol = {r["symbol"]: {"total": r["cnt"], "wins": r["wins"] or 0} for r in cur.fetchall()}

    total = row["total_evaluated"] or 0
    correct = row["correct"] or 0

    return {
        "signals_tracked": total,
        "overall_win_rate": round(correct / total, 4) if total > 0 else 0,
        "by_decision": by_decision,
        "by_symbol": by_symbol,
    }


def get_missed_opportunities(days: int = 7, limit: int = 50) -> Dict[str, Any]:
    """Fetch signals that were NOT executed but had positive outcomes."""
    with _db_cursor() as cur:
        cur.execute("""
            SELECT * FROM signals
            WHERE executed = 0
              AND evaluated_at IS NOT NULL
              AND was_correct = 1
              AND timestamp >= datetime('now', ?)
            ORDER BY timestamp DESC
            LIMIT ?
        """, (f"-{days} days", limit))
        rows = cur.fetchall()

    signals = []
    total_missed_pct = 0.0
    high_conf = 0
    for row in rows:
        d = dict(row)
        d["indicators"] = json.loads(d.get("indicators", "{}"))
        d["mock_data"] = bool(d.get("mock_data"))
        missed_pct = d.get("missed_profit_pct", 0) or 0
        total_missed_pct += missed_pct
        if d.get("confidence", 0) >= 80:
            high_conf += 1
        signals.append(d)

    return {
        "signals": signals,
        "aggregate": {
            "signals_missed_count": len(signals),
            "total_missed_profit_pct": round(total_missed_pct, 2),
            "avg_missed_pct": round(total_missed_pct / len(signals), 2) if signals else 0,
            "high_confidence_missed": high_conf,
        },
    }


# ── Backtest Results ─────────────────────────────────────────────────

def save_backtest_result(symbol: str, exchange: str, interval: str,
                         metrics: Dict[str, Any], config: Dict[str, Any]) -> int:
    """Save a backtest result. Returns the row ID."""
    with _db_cursor() as cur:
        cur.execute("""
            INSERT INTO backtest_results
                (symbol, exchange, interval, start_date, end_date,
                 initial_capital, win_rate, total_pnl, total_pnl_pct,
                 max_drawdown, sharpe_ratio, profit_factor, calmar_ratio,
                 total_trades, config, equity_curve)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            symbol, exchange, interval,
            config.get("start_date", ""), config.get("end_date", ""),
            config.get("initial_capital", 100000),
            metrics.get("win_rate", 0), metrics.get("total_pnl", 0),
            metrics.get("total_pnl_pct", 0), metrics.get("max_drawdown_pct", 0),
            metrics.get("sharpe_ratio", 0), metrics.get("profit_factor", 0),
            metrics.get("calmar_ratio", 0), metrics.get("total_trades", 0),
            json.dumps(config), json.dumps(metrics.get("equity_curve", [])),
        ))
        return cur.lastrowid or 0


def get_backtest_results(limit: int = 20) -> List[Dict[str, Any]]:
    """Fetch recent backtest results."""
    with _db_cursor() as cur:
        cur.execute("SELECT * FROM backtest_results ORDER BY created_at DESC LIMIT ?", (limit,))
        return [dict(r) for r in cur.fetchall()]


# ── Outcome Pending Queue ────────────────────────────────────────────

def add_pending_outcome(signal: Dict[str, Any], check_after_minutes: int = 60) -> None:
    """Add a signal to the outcome evaluation queue."""
    from datetime import timedelta
    signal_time = datetime.fromisoformat(signal.get("timestamp", datetime.now(timezone.utc).isoformat()))
    check_time = signal_time + timedelta(minutes=check_after_minutes)

    with _db_cursor() as cur:
        cur.execute("""
            INSERT OR IGNORE INTO outcome_pending
                (signal_id, symbol, exchange, decision, entry_price, signal_time, next_check_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (
            signal.get("id", ""),
            signal.get("symbol", ""),
            signal.get("exchange", "CRYPTO"),
            signal.get("decision", "HOLD"),
            signal.get("price", 0),
            signal.get("timestamp", ""),
            check_time.isoformat(),
        ))


def get_pending_outcomes(limit: int = 20) -> List[Dict[str, Any]]:
    """Get signals that are ready for outcome evaluation."""
    from datetime import datetime, timezone
    now = datetime.now(timezone.utc).isoformat()

    with _db_cursor() as cur:
        cur.execute("""
            SELECT * FROM outcome_pending
            WHERE next_check_at <= ?
              AND retry_count < 10
            ORDER BY next_check_at ASC
            LIMIT ?
        """, (now, limit))
        return [dict(r) for r in cur.fetchall()]


def remove_pending_outcome(signal_id: str) -> None:
    """Remove a signal from the outcome evaluation queue."""
    with _db_cursor() as cur:
        cur.execute("DELETE FROM outcome_pending WHERE signal_id = ?", (signal_id,))


def increment_pending_retry(signal_id: str) -> None:
    """Increment retry count for a failed outcome evaluation."""
    with _db_cursor() as cur:
        cur.execute("""
            UPDATE outcome_pending
            SET retry_count = retry_count + 1,
                next_check_at = datetime('now', '+15 minutes')
            WHERE signal_id = ?
              AND retry_count < 10
        """, (signal_id,))
