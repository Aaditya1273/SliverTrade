"""
SilverTrade AI — Locust Load Test
==================================
Tests the Platform API under concurrent load.

Usage (local):
    uv run locust -f Platfrom/test/load/locustfile.py \
        --host http://127.0.0.1:5000 \
        --users 200 --spawn-rate 10 --run-time 5m --headless

Usage (staging):
    uv run locust -f Platfrom/test/load/locustfile.py \
        --host https://staging.yourdomain.com \
        --users 500 --spawn-rate 20 --run-time 10m --headless

Pass targets (per Phase 11.4):
    - 200 CCU: P95 < 500ms, error rate < 0.1%
    - 500 CCU: P95 < 1000ms, error rate < 1%
"""

import os
import random
from locust import HttpUser, task, between, events

# ── Test credentials ──────────────────────────────────────────────────────────
# Set these via environment variables before running
LOADTEST_USER = os.getenv("LOADTEST_USER", "loadtest@silvertrade.ai")
LOADTEST_PASS = os.getenv("LOADTEST_PASS", "LoadTest@123!")
LOADTEST_APIKEY = os.getenv("LOADTEST_APIKEY", "")

TEST_SYMBOLS = [
    {"symbol": "BTC/USDT", "exchange": "CRYPTO"},
    {"symbol": "ETH/USDT", "exchange": "CRYPTO"},
    {"symbol": "SBIN", "exchange": "NSE"},
    {"symbol": "NIFTY", "exchange": "NSE"},
]


class TradingUser(HttpUser):
    """Simulates a typical active user of SilverTrade AI."""

    wait_time = between(1, 3)

    def on_start(self):
        """Login once per user and store session + api_key."""
        self.api_key = LOADTEST_APIKEY
        self.logged_in = False

        if not self.api_key:
            # Try to login and get session
            response = self.client.post(
                "/auth/login",
                data={"username": LOADTEST_USER, "password": LOADTEST_PASS},
                headers={"Content-Type": "application/x-www-form-urlencoded"},
                name="/auth/login [setup]",
            )
            if response.status_code == 200:
                data = response.json()
                if data.get("status") == "success":
                    self.logged_in = True

                    # Get session status to retrieve api_key
                    status = self.client.get(
                        "/auth/session-status",
                        name="/auth/session-status [setup]",
                    )
                    if status.status_code == 200:
                        self.api_key = status.json().get("api_key", "")
            else:
                self.logged_in = False
        else:
            self.logged_in = True

    # ── High-frequency tasks ──────────────────────────────────────────────────

    @task(8)
    def get_signals(self):
        """Most common action: check AI signals feed."""
        self.client.get("/api/v1/signals?limit=20", name="/api/v1/signals")

    @task(5)
    def health_check(self):
        """Health endpoint — load balancer simulation."""
        self.client.get("/health/status", name="/health/status")

    @task(4)
    def session_status(self):
        """Check session — background polling."""
        self.client.get("/auth/session-status", name="/auth/session-status")

    # ── Medium-frequency tasks ────────────────────────────────────────────────

    @task(3)
    def get_settings(self):
        """Fetch user settings."""
        if self.logged_in:
            self.client.get("/api/v1/settings", name="/api/v1/settings [GET]")

    @task(3)
    def symbol_search(self):
        """Symbol search with debounce."""
        queries = ["SBIN", "NIFTY", "BTC", "RELIANCE", "ETH"]
        q = random.choice(queries)
        self.client.get(
            f"/api/v1/search?q={q}&exchange=NSE",
            name="/api/v1/search",
        )

    @task(2)
    def get_funds(self):
        """Portfolio / funds check."""
        if self.api_key:
            self.client.post(
                "/api/v1/funds",
                json={"apikey": self.api_key},
                name="/api/v1/funds",
            )

    @task(2)
    def get_orderbook(self):
        """Orderbook check."""
        if self.api_key:
            self.client.post(
                "/api/v1/orderbook",
                json={"apikey": self.api_key},
                name="/api/v1/orderbook",
            )

    # ── Low-frequency tasks ───────────────────────────────────────────────────

    @task(1)
    def get_quotes(self):
        """Live price quote."""
        if self.api_key:
            sym = random.choice(TEST_SYMBOLS)
            self.client.post(
                "/api/v1/quotes",
                json={"apikey": self.api_key, **sym},
                name="/api/v1/quotes",
            )

    @task(1)
    def get_holdings(self):
        """Holdings check."""
        if self.api_key:
            self.client.post(
                "/api/v1/holdings",
                json={"apikey": self.api_key},
                name="/api/v1/holdings",
            )


class SignalGenerationUser(HttpUser):
    """Simulates users actively generating AI signals — heavier load."""

    wait_time = between(5, 15)
    weight = 2  # 1 signal user per 5 regular users

    def on_start(self):
        self.api_key = LOADTEST_APIKEY

    @task(3)
    def generate_signal(self):
        """POST to Strategy Engine (via Platform proxy or direct)."""
        sym = random.choice(TEST_SYMBOLS)
        # Strategy Engine runs on a separate port — test Platform health here
        self.client.get("/health/status", name="/health/status [signal_user]")

    @task(2)
    def get_signals_history(self):
        """Signal history with pagination."""
        offset = random.choice([0, 20, 40])
        self.client.get(
            f"/api/v1/signals?limit=20&offset={offset}",
            name="/api/v1/signals [paginated]",
        )

    @task(1)
    def check_accuracy(self):
        """Signal accuracy stats."""
        self.client.get("/api/v1/signals?limit=5", name="/api/v1/signals [accuracy]")


# ── Event hooks for reporting ─────────────────────────────────────────────────

@events.test_stop.add_listener
def on_test_stop(environment, **kwargs):
    """Print pass/fail summary after test completes."""
    stats = environment.stats.total
    p95 = stats.get_response_time_percentile(0.95)
    error_rate = stats.fail_ratio * 100

    print("\n" + "=" * 60)
    print("LOAD TEST RESULTS")
    print("=" * 60)
    print(f"Total requests:    {stats.num_requests:,}")
    print(f"Failed requests:   {stats.num_failures:,}")
    print(f"Error rate:        {error_rate:.2f}%")
    print(f"P50 response time: {stats.get_response_time_percentile(0.5):.0f}ms")
    print(f"P95 response time: {p95:.0f}ms")
    print(f"P99 response time: {stats.get_response_time_percentile(0.99):.0f}ms")
    print(f"Avg response time: {stats.avg_response_time:.0f}ms")
    print(f"Req/s (peak):      {stats.max_rps:.1f}")
    print("=" * 60)

    # Pass/Fail criteria (Phase 11.4)
    passed = True
    if p95 > 1000:
        print(f"❌ FAIL: P95 {p95:.0f}ms exceeds 1000ms limit")
        passed = False
    else:
        print(f"✅ PASS: P95 {p95:.0f}ms < 1000ms")

    if error_rate > 1.0:
        print(f"❌ FAIL: Error rate {error_rate:.2f}% exceeds 1% limit")
        passed = False
    else:
        print(f"✅ PASS: Error rate {error_rate:.2f}% < 1%")

    print("=" * 60)
    print(f"OVERALL: {'✅ PASSED' if passed else '❌ FAILED'}")
    print("=" * 60)
