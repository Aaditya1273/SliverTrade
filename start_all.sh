#!/bin/bash
# SilverTrade AI — Unified System Orchestrator
# Starts Platform, Data Service, Strategy Engine, and UI in production mode.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo ""
echo "╔══════════════════════════════════════════╗"
echo "║       SilverTrade AI — Starting up        ║"
echo "╚══════════════════════════════════════════╝"
echo ""

# ── Step 0: Kill anything occupying the ports ─────────────────────────
echo "▶ Freeing ports 5000 5005 5007 3000 8765..."
fuser -k 5000/tcp 5005/tcp 5007/tcp 3000/tcp 8765/tcp 2>/dev/null || true
sleep 1

# ── Step 1: Ensure PM2 is available ──────────────────────────────────
if [ ! -d "node_modules/pm2" ]; then
    echo "▶ Installing PM2 process manager..."
    npm install pm2 --no-save --quiet
fi

# ── Step 2: Platform — run database migrations ────────────────────────
echo "▶ Initialising Platform databases..."
cd Platfrom
uv run python -c "
from database.auth_db import init_db as auth_init
from database.settings_db import init_db as settings_init
auth_init()
settings_init()
print('  Databases OK')
" 2>/dev/null || echo "  (DB already initialised or Platform not yet configured)"
cd ..

# ── Step 3: Strategy Engine API key setup ─────────────────────────────
# Only runs if SILVERTRADE_API_KEY is not yet set in Trade_Strategies/.env
if ! grep -q "^SILVERTRADE_API_KEY=" Trade_Strategies/.env 2>/dev/null; then
    echo "▶ Setting up internal API key for Strategy Engine..."
    cd Platfrom
    uv run python ../scripts/setup_strategy_apikey.py 2>/dev/null || \
        echo "  (Skipped — run manually after first login: python scripts/setup_strategy_apikey.py)"
    cd ..
else
    echo "▶ Strategy Engine API key already configured."
fi

# ── Step 4: Strategy Engine — create models dir ───────────────────────
mkdir -p Trade_Strategies/ml/models
mkdir -p Trade_Strategies/data

# ── Step 5: UI dependencies and production build ─────────────────────
if [ ! -d "ui/node_modules" ]; then
    echo "▶ Installing UI dependencies..."
    cd ui && npm install --quiet && cd ..
fi

echo "▶ Building Next.js UI (production)..."
cd ui
npm run build 2>&1 | tail -5
if [ $? -ne 0 ]; then
    echo ""
    echo "⚠  UI build failed. Starting in dev mode as fallback."
    echo "   Fix TypeScript errors then run: npm run build"
    echo ""
fi
cd ..

# ── Step 6: Launch all services via PM2 ──────────────────────────────
echo ""
echo "▶ Launching services..."
npx pm2 start ecosystem.config.js --update-env

echo ""
echo "✅ SilverTrade AI is running"
echo ""
echo "   Dashboard    → http://localhost:3000"
echo "   Platform API → http://localhost:5000/api/docs"
echo "   Strategy API → http://localhost:5007/api/v1/health"
echo "   Data Service → http://localhost:5005"
echo ""
echo "   Logs:        npx pm2 logs"
echo "   Monitor:     npx pm2 monit"
echo "   Stop all:    npx pm2 stop all"
echo ""
