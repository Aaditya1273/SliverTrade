#!/bin/bash

# SilverTrade AI: Unified System Orchestrator
# Powered by PM2 Process Manager for a Billion-Dollar Production Standard.

echo "🧹 Preparing SilverTrade AI Unified Engine..."

# Ensure ports are free before starting
fuser -k 5000/tcp 5005/tcp 5006/tcp 5007/tcp 3000/tcp 8765/tcp 2>/dev/null || true
sleep 1

# Check if PM2 is installed locally, if not, install it quietly
if [ ! -d "node_modules/pm2" ]; then
    echo "⚙️  Installing Production Process Manager (PM2)..."
    npm install pm2 --no-save > /dev/null 2>&1
fi

echo "🚀 Launching SilverTrade AI..."
npx pm2 start ecosystem.config.js

echo ""
echo "✅ System Online."
echo "📊 To monitor logs across all services, run: npx pm2 logs"
echo "🛑 To shut down the entire system gracefully, run: npx pm2 stop all"
echo ""
echo "Access the Premium Dashboard at: http://localhost:3000"
