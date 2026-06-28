#!/usr/bin/env python3
"""Concurrency benchmark for SilverTrade AI — connection pool sizing.

Measures throughput, latency percentiles (P50/P90/P99), and error rate
under increasing concurrency (1 → 1000+ users) so operators can tune pool
sizes with data rather than guesswork.

Two modes:
  locust    — interactive web UI at http://localhost:8089
  direct    — CLI-mode ramp test with terminal report

Requirements (install first):
    pip install locust numpy requests

Usage:
    # Interactive Locust web UI (set users via browser)
    python scripts/benchmark_concurrency.py locust

    # CLI ramp test (1 → 500 users, then jumps to 1000)
    python scripts/benchmark_concurrency.py direct \\
        --base-url http://localhost:5000 \\
        --api-key <test-api-key> \\
        --max-users 1000
"""

import argparse
import json
import os
import sys
import time
from typing import Any, Dict, List

# ---------------------------------------------------------------------------
# Ensure Platfrom/ is on sys.path so imports resolve when running from
# the project root or from scripts/.
# ---------------------------------------------------------------------------
_THIS_DIR = os.path.dirname(os.path.abspath(__file__))
_PROJECT_ROOT = os.path.abspath(os.path.join(_THIS_DIR, ".."))
if _PROJECT_ROOT not in sys.path:
    sys.path.insert(0, _PROJECT_ROOT)


# ---------------------------------------------------------------------------
# Direct (CLI) mode — ramp test
# ---------------------------------------------------------------------------


def _run_direct(args: argparse.Namespace) -> None:
    """Run a direct ramp test using ``requests`` or ``httpx``."""
    try:
        import requests as http
    except ImportError:
        print("Install requests:  pip install requests")
        sys.exit(1)

    base_url = args.base_url.rstrip("/")
    api_key = args.api_key
    headers = {"X-API-Key": api_key, "Content-Type": "application/json"}
    max_users = args.max_users
    ramp_duration = args.ramp_duration or max(60, max_users // 2)

    print(f"\n{'=' * 60}")
    print(f" SilverTrade AI — Concurrency Benchmark")
    print(f"{'=' * 60}")
    print(f"  Base URL      : {base_url}")
    print(f"  Max users     : {max_users}")
    print(f"  Ramp duration : {ramp_duration}s")
    print(f"{'=' * 60}\n")

    # ------------------------------------------------------------------
    # Warmup: hit a lightweight endpoint to verify connectivity & prime
    # connection pools.
    # ------------------------------------------------------------------
    print("[warmup] Checking API connectivity...")
    try:
        resp = http.get(f"{base_url}/api/v1/health", headers=headers, timeout=10)
        resp.raise_for_status()
        print(f"[warmup] OK  (status={resp.status_code})")
    except Exception as exc:
        print(f"[warmup] FAIL — {exc}")
        print("Check that the server is running and the API key is valid.")
        sys.exit(1)

    # ------------------------------------------------------------------
    # Endpoints to hit during the ramp (mix of read & write paths).
    # Update these to reflect your actual route table.
    # ------------------------------------------------------------------
    endpoints = [
        ("GET", f"{base_url}/api/v1/health", None),
        ("GET", f"{base_url}/api/v1/quotes?symbol=NIFTY&exchange=NFO", None),
        ("GET", f"{base_url}/api/v1/symbol?symbol=NIFTY&exchange=NFO", None),
        ("GET", f"{base_url}/api/v1/search?query=NIFTY&exchange=NFO", None),
        ("POST", f"{base_url}/api/v1/orderbook", {"apikey": api_key}),
    ]

    # ------------------------------------------------------------------
    # Ramp loop
    # ------------------------------------------------------------------
    samples: List[Dict[str, Any]] = []
    errors = 0
    total_requests = 0
    chunk_size = max(1, max_users // ramp_duration)
    start_ts = time.time()

    for current_users in range(1, max_users + 1, chunk_size):
        n = min(chunk_size, max_users - current_users + 1)
        t0 = time.perf_counter()

        # Fire n requests across the endpoint mix in sequence
        for _ in range(n):
            method, url, body = endpoints[total_requests % len(endpoints)]
            try:
                inner_t0 = time.perf_counter()
                if method == "GET":
                    resp = http.get(url, headers=headers, timeout=30)
                else:
                    resp = http.post(url, json=body or {}, headers=headers, timeout=30)
                elapsed_ms = (time.perf_counter() - inner_t0) * 1000

                samples.append(
                    {
                        "users": current_users,
                        "ms": elapsed_ms,
                        "status": resp.status_code,
                        "path": url.split("/api/v1")[-1],
                    }
                )
                if resp.status_code >= 500:
                    errors += 1
            except Exception as exc:
                samples.append(
                    {
                        "users": current_users,
                        "ms": -1,
                        "status": 0,
                        "path": url.split("/api/v1")[-1],
                        "error": str(exc),
                    }
                )
                errors += 1

            total_requests += 1

        # Report progress every ~5% of the ramp
        if current_users % max(1, max_users // 20) < chunk_size:
            elapsed = time.time() - start_ts
            pct = current_users / max_users * 100
            print(
                f"  [{current_users:>5}/{max_users} users  "
                f"{elapsed:5.0f}s]  "
                f"{total_requests} requests, {errors} errors"
            )

    elapsed_total = time.time() - start_ts
    print(f"\n{'=' * 60}")
    print(f" BENCHMARK COMPLETE")
    print(f"{'=' * 60}")
    print(f"  Duration      : {elapsed_total:.0f}s")
    print(f"  Total requests: {total_requests}")
    print(f"  Errors        : {errors}  ({errors / max(1, total_requests) * 100:.1f}%)")

    # ------------------------------------------------------------------
    # Latency percentiles
    # ------------------------------------------------------------------
    latencies = sorted(s["ms"] for s in samples if s["ms"] >= 0)
    if latencies:
        import numpy as np

        arr = np.array(latencies, dtype=np.float64)
        print(f"\n  Latency (ms):")
        print(f"    P50    : {np.percentile(arr, 50):8.1f}")
        print(f"    P75    : {np.percentile(arr, 75):8.1f}")
        print(f"    P90    : {np.percentile(arr, 90):8.1f}")
        print(f"    P95    : {np.percentile(arr, 95):8.1f}")
        print(f"    P99    : {np.percentile(arr, 99):8.1f}")
        print(f"    Max    : {arr.max():8.1f}")
        print(f"    Mean   : {arr.mean():8.1f}")

    # ------------------------------------------------------------------
    # Pool sizing recommendations
    # ------------------------------------------------------------------
    print(f"\n  Connection Pool Sizing Recommendations:")
    print(f"    Recommended POOL_SIZE  = {min(2 * max_users // max(1, _get_worker_count()), 200)}")
    print(
        f"    Recommended MAX_OVERFLOW = {min(4 * max_users // max(1, _get_worker_count()), 400)}"
    )
    print(
        f"    Set via: POOL_SIZE={min(2 * max_users // max(1, _get_worker_count()), 200)} "
        f"MAX_OVERFLOW={min(4 * max_users // max(1, _get_worker_count()), 400)}"
    )

    # Save results as JSON for CI dashboards
    if args.output:
        report = {
            "duration_s": elapsed_total,
            "total_requests": total_requests,
            "errors": errors,
            "error_rate_pct": round(errors / max(1, total_requests) * 100, 2),
            "latency_ms": {
                "p50": round(float(np.percentile(arr, 50)), 1) if latencies else 0,
                "p90": round(float(np.percentile(arr, 90)), 1) if latencies else 0,
                "p99": round(float(np.percentile(arr, 99)), 1) if latencies else 0,
                "mean": round(float(arr.mean()), 1) if latencies else 0,
            },
            "pool_sizing": {
                "recommended_pool_size": min(2 * max_users // max(1, _get_worker_count()), 200),
                "recommended_max_overflow": min(4 * max_users // max(1, _get_worker_count()), 400),
            },
        }
        with open(args.output, "w") as f:
            json.dump(report, f, indent=2)
        print(f"\n  Report saved to: {args.output}")

    print()


def _get_worker_count() -> int:
    """Return the number of gunicorn workers from env or CPU count."""
    workers = os.getenv("GUNICORN_WORKERS")
    if workers:
        return int(workers)
    return os.cpu_count() or 4


# ---------------------------------------------------------------------------
# Locust mode — interactive web UI
# ---------------------------------------------------------------------------

LOCUST_FILE = os.path.join(_THIS_DIR, "_locustfile.py")


def _run_locust(args: argparse.Namespace) -> None:
    """Generate a locustfile and launch locust."""
    locustfile_content = f'''"""Auto-generated locustfile for SilverTrade AI benchmark.

Generated by: python scripts/benchmark_concurrency.py locust
"""

import json
from locust import HttpUser, task, between


class SilverTradeUser(HttpUser):
    """Simulates a SilverTrade AI API user."""

    wait_time = between({args.min_wait or 1}, {args.max_wait or 5})

    API_KEY = "{args.api_key or ""}"

    def on_start(self):
        """Verify connectivity on worker start."""
        resp = self.client.get("/api/v1/health", headers=self._headers(), timeout=10)
        if resp.status_code >= 400:
            self.environment.runner.quit()
            raise RuntimeError(f"Health check failed: {{resp.status_code}}")

    def _headers(self):
        return {{"X-API-Key": self.API_KEY, "Content-Type": "application/json"}}

    @task(3)
    def health(self):
        self.client.get("/api/v1/health", headers=self._headers())

    @task(3)
    def quotes(self):
        self.client.get(
            "/api/v1/quotes?symbol=NIFTY&exchange=NFO",
            headers=self._headers(),
        )

    @task(2)
    def search(self):
        self.client.get(
            "/api/v1/search?query=NIFTY&exchange=NFO",
            headers=self._headers(),
        )

    @task(2)
    def orderbook(self):
        self.client.post(
            "/api/v1/orderbook",
            json={{"apikey": self.API_KEY}},
            headers=self._headers(),
        )

    @task(1)
    def place_order(self):
        self.client.post(
            "/api/v1/placeorder",
            json={{
                "apikey": self.API_KEY,
                "symbol": "NIFTY",
                "exchange": "NFO",
                "action": "BUY",
                "quantity": 1,
                "product": "MIS",
                "pricetype": "MARKET",
            }},
            headers=self._headers(),
        )
'''

    with open(LOCUST_FILE, "w") as f:
        f.write(locustfile_content)

    print(f"  Generated locustfile: {LOCUST_FILE}")
    print(f"  Starting locust web UI at http://localhost:8089")
    print()
    sys.stdout.flush()

    # Launch locust — it handles its own argument parsing
    import locust.main

    locust_args = [
        "locust",
        "-f",
        LOCUST_FILE,
        "--host",
        args.base_url,
        "--web-host",
        args.locust_web_host or "127.0.0.1",
        "--web-port",
        str(args.locust_web_port or 8089),
    ]
    if args.headless:
        locust_args.extend(
            [
                "--headless",
                "-u",
                str(args.max_users),
                "-r",
                str(args.spawn_rate or 10),
                "--run-time",
                args.run_time or "5m",
                "--html",
                args.html_report or "benchmark_report.html",
            ]
        )

    sys.argv = locust_args
    locust.main.main()


# ---------------------------------------------------------------------------
# CLI entry point
# ---------------------------------------------------------------------------


def main():
    parser = argparse.ArgumentParser(
        description="SilverTrade AI — concurrency benchmark",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    sub = parser.add_subparsers(dest="mode", required=True)

    # --- direct subcommand ---
    direct = sub.add_parser("direct", help="CLI ramp test with terminal report")
    direct.add_argument("--base-url", default="http://localhost:5000", help="Server base URL")
    direct.add_argument("--api-key", default="", help="API key for auth")
    direct.add_argument("--max-users", type=int, default=200, help="Target concurrency level")
    direct.add_argument("--ramp-duration", type=int, default=0, help="Ramp-up duration in seconds")
    direct.add_argument("--output", default="", help="Path to save JSON report (optional)")

    # --- locust subcommand ---
    locust_parser = sub.add_parser("locust", help="Interactive Locust web UI")
    locust_parser.add_argument(
        "--base-url", default="http://localhost:5000", help="Server base URL"
    )
    locust_parser.add_argument("--api-key", default="", help="API key for auth")
    locust_parser.add_argument("--locust-web-host", default="127.0.0.1", help="Locust web UI host")
    locust_parser.add_argument(
        "--locust-web-port", type=int, default=8089, help="Locust web UI port"
    )
    locust_parser.add_argument(
        "--min-wait", type=float, default=1.0, help="Min think time (seconds)"
    )
    locust_parser.add_argument(
        "--max-wait", type=float, default=5.0, help="Max think time (seconds)"
    )

    # Headless mode (CI use)
    locust_parser.add_argument("--headless", action="store_true", help="Run headless (no web UI)")
    locust_parser.add_argument("--max-users", type=int, default=200, help="Target users (headless)")
    locust_parser.add_argument(
        "--spawn-rate", type=int, default=10, help="Users spawned per second"
    )
    locust_parser.add_argument("--run-time", default="5m", help="Test duration (e.g. 5m, 30s)")
    locust_parser.add_argument(
        "--html-report", default="benchmark_report.html", help="HTML report path"
    )

    args = parser.parse_args()

    if args.mode == "direct":
        _run_direct(args)
    elif args.mode == "locust":
        _run_locust(args)


if __name__ == "__main__":
    main()
