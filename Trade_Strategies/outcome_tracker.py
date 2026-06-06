"""
SilverTrade AI — Signal Outcome Tracker
=========================================
Background job that evaluates the accuracy of generated signals.

For every signal generated:
1. Record the entry price at signal time.
2. After 1 hour (configurable), fetch the actual price.
3. Compare to determine if signal was correct.
4. Record outcome in the database (win/loss, P&L %).

Runs as an APScheduler job inside the Strategy Engine.
"""

import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, Optional

import requests

from database import (
    add_pending_outcome,
    get_pending_outcomes,
    increment_pending_retry,
    remove_pending_outcome,
    update_signal_outcome,
)

logger = logging.getLogger(__name__)

PLATFORM_HOST = os.getenv("SILVERTRADE_HOST", "http://platform:5000")
PLATFORM_API_KEY = os.getenv("SILVERTRADE_API_KEY", "")


class OutcomeTracker:
    """Evaluates signal outcomes by comparing predicted vs actual price movements.

    Runs every 15 minutes via APScheduler, checking for signals that are
    ready for evaluation (>= 1 hour since generation).
    """

    def __init__(self):
        self._enabled = True

    def run_pending_evaluations(self) -> int:
        """Check all signals due for outcome evaluation.

        Returns:
            Number of signals evaluated this cycle.
        """
        if not self._enabled:
            logger.debug("OutcomeTracker is disabled")
            return 0

        pending = get_pending_outcomes(limit=25)
        if not pending:
            return 0

        evaluated = 0
        for signal in pending:
            try:
                self._evaluate(signal)
                evaluated += 1
            except Exception as e:
                logger.error("Failed to evaluate signal %s: %s", signal.get("signal_id"), e)
                increment_pending_retry(signal["signal_id"])

        return evaluated

    def _evaluate(self, signal: Dict[str, Any]) -> None:
        """Evaluate a single signal's outcome."""
        signal_id = signal["signal_id"]
        symbol = signal["symbol"]
        exchange = signal.get("exchange", "CRYPTO")
        entry_price = signal["entry_price"]
        decision = signal["decision"]
        signal_time = signal.get("signal_time", "")

        # Fetch current price
        current_price = self._fetch_current_price(symbol, exchange)

        if current_price is None or current_price <= 0:
            logger.warning("Could not fetch price for %s — will retry", symbol)
            increment_pending_retry(signal_id)
            return

        # Calculate outcome
        outcome_pct = (current_price - entry_price) / entry_price * 100

        if decision == "BUY":
            was_correct = outcome_pct > 0
            missed_profit_pct = outcome_pct if outcome_pct > 0 else 0
        elif decision == "SELL":
            was_correct = outcome_pct < 0
            missed_profit_pct = abs(outcome_pct) if outcome_pct < 0 else 0
        else:
            was_correct = None
            missed_profit_pct = 0

        # Record outcome in DB
        update_signal_outcome(
            signal_id=signal_id,
            outcome_price=current_price,
            outcome_pct=round(outcome_pct, 2),
            was_correct=was_correct if was_correct is not None else False,
            missed_profit_pct=round(missed_profit_pct, 2),
        )

        # Remove from pending queue
        remove_pending_outcome(signal_id)

        logger.info(
            "Signal %s (%s %s): entry=%.2f current=%.2f outcome=%.2f%% %s",
            signal_id, symbol, decision,
            entry_price, current_price, outcome_pct,
            "CORRECT" if was_correct else "INCORRECT" if was_correct is not None else "NEUTRAL",
        )

    def _fetch_current_price(self, symbol: str, exchange: str) -> Optional[float]:
        """Fetch the latest traded price from the Platform API.

        Returns None if the price cannot be fetched (will retry next cycle).
        """
        try:
            url = f"{PLATFORM_HOST}/api/v1/quotes"
            payload = {
                "apikey": PLATFORM_API_KEY,
                "symbol": symbol,
                "exchange": exchange,
            }
            response = requests.post(url, json=payload, timeout=15)
            data = response.json()

            if data.get("status") == "error":
                return None

            # The quote endpoint may return data in different formats
            quote = data.get("data") or data.get("quotes") or data
            if isinstance(quote, dict):
                return float(quote.get("ltp", quote.get("last_price", quote.get("close", 0))))
            return None

        except Exception as e:
            logger.debug("Failed to fetch price for %s: %s", symbol, e)
            return None

    def schedule_evaluation(self, signal: Dict[str, Any], check_after_minutes: int = 60) -> None:
        """Schedule a signal for future outcome evaluation.

        Called immediately after a signal is generated.
        """
        add_pending_outcome(signal, check_after_minutes=check_after_minutes)

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False
