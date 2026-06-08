"""
SilverTrade AI — Load Testing Script (Phase 11)
=============================================
Locust load testing for 200 concurrent users against real API endpoints.
"""

from locust import HttpUser, task, between
import random


class TradingUser(HttpUser):
    """Simulates a real trader using the platform."""

    wait_time = between(1, 3)

    def on_start(self):
        """Initialize with a test API key."""
        self.user_id = self.environment.runner.user_count
        self.api_key = f"load_test_key_{self.user_id}"

    @task(5)  # Most common: health check + status
    def health_check(self):
        """Health endpoints — constantly polled by load balancers and monitoring."""
        self.client.get(
            '/health/status',
            name='/health/status'
        )

    @task(4)  # Common: check dashboard / landing page
    def landing_page(self):
        """Fetch the main app (cached HTML)."""
        self.client.get(
            '/',
            name='/ (landing page)'
        )

    @task(3)  # Common: fetch trading signals
    def get_signals(self):
        """Fetch AI trading signals."""
        self.client.get(
            '/api/v1/signals/',
            name='/api/v1/signals/'
        )

    @task(2)  # Less common: health check details
    def detailed_health(self):
        """Detailed health check with DB status."""
        self.client.get(
            '/health/check',
            name='/health/check'
        )

    @task(2)  # Chat requests
    def chat_request(self):
        """Send a chat message."""
        questions = [
            'What is the current market status?',
            'Show me recent trading signals',
            'What indicators are you using?',
        ]
        message = random.choice(questions)
        self.client.post(
            '/api/v1/chat',
            json={
                'apikey': self.api_key,
                'message': message,
                'conversation_id': f'loadtest_{self.user_id}'
            },
            name='/api/v1/chat'
        )

    @task(2)  # Fetch config endpoints
    def get_config(self):
        """Fetch app configuration."""
        self.client.get(
            '/api/config/host',
            name='/api/config/host'
        )

    @task(1)  # Rare: fetch latest signal
    def get_latest_signal(self):
        """Fetch the most recent signal."""
        self.client.get(
            '/api/v1/signals/latest',
            name='/api/v1/signals/latest'
        )
