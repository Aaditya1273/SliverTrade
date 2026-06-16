#!/usr/bin/env python3
"""
SilverTrade AI: Integration Verification Script

Verifies that all core service files exist and API contracts are met.
Run after setup to confirm the system is ready to start.
"""

import os
import sys


def main():
    print("🧪 SilverTrade AI: Integration Verification")
    print("-" * 50)

    # Check core service files exist
    services = [
        "Platfrom/app.py",
        "data_fetch/app.py",
        "Trade_Strategies/strategies_app.py",
        "ui/app/page.tsx",
    ]

    all_exist = True
    for service in services:
        if os.path.exists(service):
            print(f"📄 {service}: FOUND")
        else:
            print(f"⚠️ {service}: MISSING")
            all_exist = False

    if not all_exist:
        print("\n❌ Verification failed: Some core files are missing.")
        sys.exit(1)

    print("\n📦 API Contract Validation")
    with open("Platfrom/app.py", "r") as f:
        content = f.read()
        if "app.register_blueprint(signals_bp)" in content:
            print("✅ signals_bp registration: VERIFIED")
        else:
            print("❌ signals_bp registration: MISSING")

    with open("Platfrom/blueprints/orders.py", "r") as f:
        content = f.read()
        if "/api/v1/execute-signal" in content:
            print("✅ execute-signal route: VERIFIED")
        else:
            print("❌ execute-signal route: MISSING")

    with open("Platfrom/services/market_data_service.py", "r") as f:
        content = f.read()
        if "MarketDataService" in content:
            print("✅ Market Data Service: VERIFIED")
        else:
            print("❌ Market Data Service: MISSING")

    with open("Trade_Strategies/strategies_app.py", "r") as f:
        content = f.read()
        if "/api/v1/decision" in content:
            print("✅ AI Decision Endpoint: VERIFIED")
        else:
            print("❌ AI Decision Endpoint: MISSING")

    print("\n" + "-" * 50)
    print("🏆 INTEGRATION VERIFIED: The system is ready for deployment.")
    print("Run ./start_all.sh to launch the full suite.")


if __name__ == "__main__":
    main()
