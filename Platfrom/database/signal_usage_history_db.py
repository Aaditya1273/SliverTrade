"""
SilverTrade AI — Signal Usage History Database
================================================
Archives per-user monthly signal usage *before* the counter is reset
on the 1st of each month.  Retained indefinitely for billing analytics
and usage trend visualisation.

Schema
------
``signal_usage_history``
    id                  INTEGER PRIMARY KEY
    user_id             INTEGER NOT NULL
    month_year          TEXT    NOT NULL   — "2026-05"
    signals_used        INTEGER NOT NULL
    signals_limit       INTEGER            — plan limit *at the time of reset*
    plan_at_time        TEXT               — user's plan when the snapshot was taken
    recorded_at         DATETIME           — when the snapshot was archived
"""

import logging

from sqlalchemy import Column, DateTime, Integer, String, Index
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import scoped_session, sessionmaker

from database.db_config import get_db_engine
from database.db_init_helper import init_db_with_logging

logger = logging.getLogger(__name__)

engine = get_db_engine()
db_session = scoped_session(sessionmaker(autocommit=False, autoflush=False, bind=engine))
Base = declarative_base()
Base.query = db_session.query_property()


class SignalUsageHistory(Base):
    """Archived snapshot of a user's signal usage at the end of a billing period."""

    __tablename__ = "signal_usage_history"

    id = Column(Integer, primary_key=True)
    user_id = Column(Integer, nullable=False)
    month_year = Column(String(7), nullable=False)  # "2026-05"
    signals_used = Column(Integer, nullable=False, default=0)
    signals_limit = Column(Integer, nullable=True)
    plan_at_time = Column(String(20), nullable=True)  # free | pro | enterprise
    recorded_at = Column(DateTime, nullable=True)

    __table_args__ = (
        Index("idx_signal_history_user_month", "user_id", "month_year", unique=True),
        Index("idx_signal_history_month", "month_year"),
    )


def archive_user_signal_usage(user_id: int, signals_used: int, signals_limit: int | None,
                              plan: str | None, recorded_at) -> SignalUsageHistory | None:
    """Insert a single usage history snapshot for a user.

    Uses an upsert-style insert that silently skips if a record for the
    same ``(user_id, month_year)`` already exists (e.g. on retry after a
    partial reset failure).

    Returns the new/existing row, or ``None`` on failure.
    """
    try:
        from datetime import datetime

        # Build month_year from current-ish time
        if recorded_at is None:
            recorded_at = datetime.utcnow()
        month_year = recorded_at.strftime("%Y-%m")

        # Check for existing entry to avoid duplicates on retry
        existing = (
            SignalUsageHistory.query
            .filter_by(user_id=user_id, month_year=month_year)
            .first()
        )
        if existing:
            logger.debug(
                f"[SignalUsageHistory] Record for user {user_id}/{month_year} "
                f"already exists (signals_used={existing.signals_used}) — skipping"
            )
            return existing

        record = SignalUsageHistory(
            user_id=user_id,
            month_year=month_year,
            signals_used=signals_used,
            signals_limit=signals_limit,
            plan_at_time=plan,
            recorded_at=recorded_at,
        )
        db_session.add(record)
        db_session.commit()
        return record
    except Exception as e:
        logger.exception(f"[SignalUsageHistory] Failed to archive usage for user {user_id}: {e}")
        db_session.rollback()
        return None
    finally:
        db_session.remove()


def get_usage_history_for_user(user_id: int, limit: int = 12) -> list[SignalUsageHistory]:
    """Return the most recent usage snapshots for a given user, newest first."""
    try:
        return (
            SignalUsageHistory.query
            .filter_by(user_id=user_id)
            .order_by(SignalUsageHistory.recorded_at.desc())
            .limit(limit)
            .all()
        )
    except Exception as e:
        logger.exception(f"[SignalUsageHistory] Failed to fetch history for user {user_id}: {e}")
        return []
    finally:
        db_session.remove()


def init_db():
    """Ensure the ``signal_usage_history`` table exists."""
    init_db_with_logging(Base, engine, "Signal Usage History DB", logger)
