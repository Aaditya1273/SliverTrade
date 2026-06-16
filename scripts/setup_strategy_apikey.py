#!/usr/bin/env python3
"""
SilverTrade AI — Strategy Engine API Key Setup
==============================================
Creates a dedicated internal API key for the Strategy Engine to call
the Platform's /api/v1/history endpoint.

Run this ONCE after first login:
    cd /home/bajrangi/Wins/silvertrade
    uv run --directory Platfrom python ../scripts/setup_strategy_apikey.py

This will:
1. Create/retrieve an internal API key for a 'strategy-engine' user
2. Write SILVERTRADE_API_KEY=<key> to Trade_Strategies/.env
3. Update ecosystem.config.js env with the key
"""

import os
import sys

# Add Platform to path
PLATFORM_DIR = os.path.join(os.path.dirname(__file__), '..', 'Platfrom')
sys.path.insert(0, PLATFORM_DIR)
os.chdir(PLATFORM_DIR)

# Load env
from dotenv import load_dotenv
load_dotenv(os.path.join(PLATFORM_DIR, '.env'))

STRATEGY_ENV = os.path.join(PLATFORM_DIR, '..', 'Trade_Strategies', '.env')
INTERNAL_USER = 'strategy-engine'


def main():
    try:
        from database.auth_db import (
            get_api_key_for_tradingview,
            generate_api_key,
            upsert_user_with_api_key,
        )
        from database.auth_db import init_db
        init_db()

        api_key = get_api_key_for_tradingview(INTERNAL_USER)
        if not api_key:
            # Create a fresh internal API key
            api_key = generate_api_key()
            upsert_user_with_api_key(INTERNAL_USER, api_key, broker='internal')
            print(f"[+] Created internal API key for '{INTERNAL_USER}'")
        else:
            print(f"[=] Found existing API key for '{INTERNAL_USER}'")

        print(f"    Key: {api_key[:8]}...{api_key[-4:]}")

        # Write to Trade_Strategies/.env
        _write_env(STRATEGY_ENV, 'SILVERTRADE_API_KEY', api_key)
        print(f"[+] Written SILVERTRADE_API_KEY to {STRATEGY_ENV}")
        print()
        print("Restart services: npx pm2 restart all")

    except ImportError as e:
        print(f"[!] Import error: {e}")
        print("    Run this from the Platfrom directory with: uv run python ../scripts/setup_strategy_apikey.py")
        sys.exit(1)
    except Exception as e:
        print(f"[!] Error: {e}")
        sys.exit(1)


def _write_env(env_path: str, key: str, value: str):
    """Write or update a key=value line in a .env file."""
    lines = []
    found = False

    if os.path.exists(env_path):
        with open(env_path) as f:
            lines = f.readlines()

        for i, line in enumerate(lines):
            if line.startswith(f'{key}=') or line.startswith(f'{key} ='):
                lines[i] = f'{key}={value}\n'
                found = True
                break

    if not found:
        lines.append(f'{key}={value}\n')

    os.makedirs(os.path.dirname(os.path.abspath(env_path)), exist_ok=True)
    with open(env_path, 'w') as f:
        f.writelines(lines)


if __name__ == '__main__':
    main()
