"""
SilverTrade AI — Monthly Signal Limit Reset Service
====================================================
Resets ``users.signals_used_this_month`` to 0 on the 1st of every
month at 00:01 IST using APScheduler.

This prevents the per-user monthly signal cap from accumulating
indefinitely.  The job is idempotent — running it mid-month is a
no-op for users whose counter is already 0.
"""

import logging
import threading

import pytz
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

# IST timezone for market-aligned scheduling
IST = pytz.timezone("Asia/Kolkata")

# Global scheduler instance (lazy-initialized)
_scheduler: BackgroundScheduler | None = None
_lock = threading.Lock()
_initialized = False

JOB_ID = "monthly_signal_limit_reset"


def _reset_all_signal_counters():
    """Archive current signal usage for every user, then reset counters
    and stamp ``last_signal_reset_at`` with the current UTC time.

    Archiving happens first so that historical analytics are preserved
    before the monthly counter is zeroed.

    Runs in the APScheduler worker thread.
    """
    try:
        from database.user_db import User, db_session
        from database.signal_usage_history_db import archive_user_signal_usage
        from sqlalchemy import update
        from datetime import datetime

        now = datetime.utcnow()

        # ── 1. Archive current usage before reset ──
        users = User.query.all()
        archived_count = 0
        for user in users:
            used = user.signals_used_this_month or 0
            if used > 0:
                archive_user_signal_usage(
                    user_id=user.id,
                    signals_used=used,
                    signals_limit=user.signals_limit,
                    plan=user.plan,
                    recorded_at=now,
                )
                archived_count += 1

        # ── 2. Reset counters ──
        stmt = update(User).values(
            signals_used_this_month=0,
            last_signal_reset_at=now,
        )
        db_session.execute(stmt)
        db_session.commit()

        count = User.query.count()
        logger.info(
            f"[SignalReset] Archived {archived_count} user(s) usage, "
            f"reset signals_used_this_month for {count} user(s) "
            f"(last_reset={now.isoformat()})"
        )
    except Exception as e:
        logger.exception(f"[SignalReset] Failed to reset signal counters: {e}")
        try:
            db_session.rollback()
        except Exception:
            pass
    finally:
        # Release the scoped session for this background thread
        db_session.remove()


def init_signal_reset_scheduler():
    """Initialise and start the monthly signal reset cron job.

    Safe to call multiple times — the second and subsequent calls are
    no-ops once the scheduler has been started.
    """
    global _scheduler, _initialized

    if _initialized:
        return

    with _lock:
        if _initialized:
            return

        try:
            _scheduler = BackgroundScheduler(
                daemon=True,
                timezone=IST,
                job_defaults={
                    "coalesce": True,          # Only fire once if multiple missed
                    "max_instances": 1,         # Never overlap
                    "misfire_grace_time": 86400,  # Catch up within 24 hours
                },
            )

            # Cron: 1st of every month at 00:01 IST
            _scheduler.add_job(
                _reset_all_signal_counters,
                trigger=CronTrigger(day=1, hour=0, minute=1, timezone=IST),
                id=JOB_ID,
                name="Monthly signal limit reset",
                replace_existing=True,
            )

            _scheduler.start()
            _initialized = True
            logger.info(
                "[SignalReset] Monthly cron scheduled: 1st of each month at 00:01 IST"
            )
        except Exception as e:
            logger.exception(f"[SignalReset] Failed to initialise scheduler: {e}")
            raise


def get_signal_reset_scheduler() -> BackgroundScheduler | None:
    """Return the global scheduler instance, or ``None`` if not yet initialised."""
    return _scheduler


def trigger_manual_reset():
    """Manually trigger the signal counter reset on-demand.

    Wraps ``_reset_all_signal_counters`` with manual-trigger logging.
    Intended for admin testing and manual intervention.
    """
    logger.info("[SignalReset] Manual reset triggered by admin")
    _reset_all_signal_counters()


def shutdown_signal_reset_scheduler():
    """Gracefully shut down the scheduler (called during app teardown)."""
    global _scheduler, _initialized
    if _scheduler:
        try:
            _scheduler.shutdown(wait=False)
        except Exception as e:
            logger.warning(f"[SignalReset] Scheduler shutdown error: {e}")
        finally:
            _scheduler = None
            _initialized = False
            logger.info("[SignalReset] Scheduler shut down")
