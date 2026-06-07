"""
SilverTrade AI — Alerts Engine
==============================
Manages alert rules and sends notifications for trading signals.

Alert types:
- Signal alert: Send notification when a new BUY/SELL signal is generated
- Confidence threshold: Only alert if confidence >= X%
- Symbol-specific: Alert for specific symbols only
"""

import json
import logging
import os
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

import requests

from database import get_alert_rules, save_alert_rule

logger = logging.getLogger(__name__)

PLATFORM_HOST = os.getenv("SILVERTRADE_HOST", "http://platform:5000")
PLATFORM_API_KEY = os.getenv("SILVERTRADE_API_KEY", "")


class AlertsEngine:
    """Manages alert rules and sends notifications for trading signals."""

    def __init__(self):
        self._enabled = True

    def check_and_send_alert(self, signal: Dict[str, Any]) -> None:
        """Check if signal matches any alert rules and send notifications."""
        if not self._enabled:
            return

        rules = get_alert_rules()
        if not rules:
            return

        for rule in rules:
            if self._signal_matches_rule(signal, rule):
                self._send_notification(signal, rule)

    def _signal_matches_rule(self, signal: Dict[str, Any], rule: Dict[str, Any]) -> bool:
        """Check if a signal matches an alert rule."""
        # Check if alerts are enabled
        if not rule.get("enabled", True):
            return False

        # Check confidence threshold
        min_confidence = rule.get("min_confidence", 50)
        if signal.get("confidence", 0) < min_confidence:
            return False

        # Check symbol filter
        symbols = rule.get("symbols", [])
        if symbols and signal.get("symbol") not in symbols:
            return False

        # Check quiet hours
        quiet_start = rule.get("quiet_hours_start")
        quiet_end = rule.get("quiet_hours_end")
        if quiet_start and quiet_end:
            current_hour = datetime.now(timezone.utc).hour
            if quiet_start <= current_hour < quiet_end:
                return False

        # Check decision type (BUY/SELL only, not HOLD)
        decision = signal.get("decision")
        if decision == "HOLD":
            return False

        return True

    def _send_notification(self, signal: Dict[str, Any], rule: Dict[str, Any]) -> None:
        """Send notification via configured channels."""
        channels = rule.get("channels", ["browser"])

        for channel in channels:
            try:
                if channel == "browser":
                    self._send_browser_push(signal)
                elif channel == "telegram":
                    self._send_telegram_alert(signal)
                elif channel == "email":
                    self._send_email_alert(signal)
            except Exception as e:
                logger.error("Failed to send %s notification: %s", channel, e)

    def _send_browser_push(self, signal: Dict[str, Any]) -> None:
        """Send browser push notification via Platform."""
        try:
            url = f"{PLATFORM_HOST}/api/v1/push/notify"
            payload = {
                "apikey": PLATFORM_API_KEY,
                "title": f"SilverTrade Signal: {signal.get('decision')} {signal.get('symbol')}",
                "body": f"Confidence: {signal.get('confidence')}% - {signal.get('reasoning', '')[:100]}",
                "data": {
                    "signal_id": signal.get("id"),
                    "symbol": signal.get("symbol"),
                    "decision": signal.get("decision"),
                },
            }
            response = requests.post(url, json=payload, timeout=5)
            logger.info("Browser push sent: %s", response.status_code)
        except Exception as e:
            logger.error("Browser push failed: %s", e)

    def _send_telegram_alert(self, signal: Dict[str, Any]) -> None:
        """Send Telegram alert via Platform."""
        try:
            url = f"{PLATFORM_HOST}/api/v1/telegram/notify"
            payload = {
                "apikey": PLATFORM_API_KEY,
                "message": (
                    f"🚀 SilverTrade Signal\n"
                    f"Symbol: {signal.get('symbol')}\n"
                    f"Decision: {signal.get('decision')}\n"
                    f"Confidence: {signal.get('confidence')}%\n"
                    f"Price: ${signal.get('price', 0):.2f}\n\n"
                    f"{signal.get('reasoning', '')[:200]}"
                ),
            }
            response = requests.post(url, json=payload, timeout=5)
            logger.info("Telegram alert sent: %s", response.status_code)
        except Exception as e:
            logger.error("Telegram alert failed: %s", e)

    def _send_email_alert(self, signal: Dict[str, Any]) -> None:
        """Send email alert via Platform."""
        try:
            url = f"{PLATFORM_HOST}/api/v1/email/notify"
            payload = {
                "apikey": PLATFORM_API_KEY,
                "subject": f"SilverTrade Signal: {signal.get('decision')} {signal.get('symbol')}",
                "body": json.dumps(signal, indent=2),
            }
            response = requests.post(url, json=payload, timeout=5)
            logger.info("Email alert sent: %s", response.status_code)
        except Exception as e:
            logger.error("Email alert failed: %s", e)

    @property
    def is_enabled(self) -> bool:
        return self._enabled

    def enable(self) -> None:
        self._enabled = True

    def disable(self) -> None:
        self._enabled = False
