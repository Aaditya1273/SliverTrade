#!/bin/bash
# SilverTrade AI — Production Deploy Script
# ==========================================
# Pulls latest code, builds UI, restarts services with zero downtime.
# Run on your production server after pushing to main.
#
# Usage:
#   ./deploy.sh              # Full deploy (pull + build + restart)
#   ./deploy.sh --hotfix     # Skip UI build (backend-only fix)
#   ./deploy.sh --ui-only    # Rebuild UI only, skip backend restart

set -euo pipefail

HOTFIX=false
UI_ONLY=false
for arg in "$@"; do
    case $arg in
        --hotfix)   HOTFIX=true ;;
        --ui-only)  UI_ONLY=true ;;
    esac
done

echo ""
echo "╔══════════════════════════════════════╗"
echo "║   SilverTrade AI — Production Deploy  ║"
echo "╚══════════════════════════════════════╝"
echo ""
echo "Mode: $([ "$HOTFIX" = true ] && echo 'Hotfix (no UI build)' || ([ "$UI_ONLY" = true ] && echo 'UI only' || echo 'Full deploy'))"
echo "Time: $(date '+%Y-%m-%d %H:%M:%S')"
echo ""

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

# ── Step 1: Pull latest code ─────────────────────────────────────────────────
if [ "$UI_ONLY" = false ]; then
    echo "▶ Pulling latest code..."
    git fetch origin main
    git reset --hard origin/main
    echo "  $(git log -1 --pretty='%h %s')"
fi

# ── Step 2: Build Next.js UI ──────────────────────────────────────────────────
if [ "$HOTFIX" = false ]; then
    echo ""
    echo "▶ Building UI..."
    if [ ! -d "ui/node_modules" ]; then
        echo "  Installing npm dependencies..."
        npm install --prefix ui --quiet
    fi

    npm run build --prefix ui 2>&1 | tail -8
    echo "  UI build complete"
fi

# ── Step 3: Reload Platform (graceful — no connection drop) ──────────────────
if [ "$UI_ONLY" = false ]; then
    echo ""
    echo "▶ Reloading Platform backend..."
    npx pm2 reload SilverTrade-Platform --update-env 2>/dev/null || \
        npx pm2 restart SilverTrade-Platform --update-env
    sleep 2

    echo "▶ Reloading Strategy Engine..."
    npx pm2 reload SilverTrade-AI-Engine --update-env 2>/dev/null || \
        npx pm2 restart SilverTrade-AI-Engine --update-env
    sleep 2
fi

# ── Step 4: Restart UI ───────────────────────────────────────────────────────
echo ""
echo "▶ Restarting UI service..."
npx pm2 restart SilverTrade-UI --update-env
sleep 3

# ── Step 5: Health check ─────────────────────────────────────────────────────
echo ""
echo "▶ Running health checks..."

PLATFORM_OK=false
UI_OK=false
STRATEGY_OK=false

for i in 1 2 3 4 5; do
    if curl -sf http://127.0.0.1:5000/health/status > /dev/null 2>&1; then
        PLATFORM_OK=true
        break
    fi
    sleep 2
done

for i in 1 2 3; do
    if curl -sf http://127.0.0.1:3000 > /dev/null 2>&1; then
        UI_OK=true
        break
    fi
    sleep 2
done

for i in 1 2 3; do
    if curl -sf http://127.0.0.1:5007/api/v1/health > /dev/null 2>&1; then
        STRATEGY_OK=true
        break
    fi
    sleep 2
done

echo ""
echo "  Platform:        $([ "$PLATFORM_OK" = true ] && echo '✅ OK' || echo '❌ FAILED')"
echo "  UI:              $([ "$UI_OK" = true ] && echo '✅ OK' || echo '❌ FAILED')"
echo "  Strategy Engine: $([ "$STRATEGY_OK" = true ] && echo '✅ OK' || echo '❌ FAILED')"

if [ "$PLATFORM_OK" = false ] || [ "$UI_OK" = false ]; then
    echo ""
    echo "⚠️  One or more services failed health check."
    echo "   Check logs: npx pm2 logs --lines 50"
    exit 1
fi

echo ""
echo "✅ Deploy complete — $(date '+%H:%M:%S')"
echo ""
echo "   Dashboard → http://localhost:3000"
echo "   Logs      → npx pm2 logs"
echo ""
