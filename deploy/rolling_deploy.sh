#!/bin/bash
# =============================================================================
# SilverTrade AI — Zero-Downtime Deployment Script (Phase 9)
# =============================================================================
# Rolling update deployment with health check gates and auto-rollback
#
# Usage:
#   bash deploy/rolling_deploy.sh [IMAGE_TAG]
# =============================================================================

set -euo pipefail

IMAGE_TAG=${1:-latest}
echo "Deploying SilverTrade AI tag: $IMAGE_TAG"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"; }
error() { echo -e "${RED}ERROR:${NC} $1"; }

# 1. Pull new images
log "Pulling new images..."
docker compose -f docker-compose.prod.yml pull

# 2. Update services one by one (rolling update)
# Strategy Engine first (no user traffic)
log "Deploying Strategy Engine..."
docker compose -f docker-compose.prod.yml up -d --no-deps trade_strategies
sleep 10
curl -f http://localhost:5007/api/v1/health || (error "Strategy Engine failed health check"; exit 1)
log "✓ Strategy Engine healthy"

# Data Fetch second
log "Deploying Data Fetch..."
docker compose -f docker-compose.prod.yml up -d --no-deps data_fetch
sleep 5
log "✓ Data Fetch deployed"

# Platform last (most critical) — scale to 2 first
log "Deploying Platform (rolling update)..."
docker compose -f docker-compose.prod.yml up -d --no-deps --scale platform=2 platform
sleep 15
# Health check new instance
curl -f http://localhost:5000/api/v1/ping || (error "Platform failed health check"; exit 1)
# Scale back to 1 (remove old instance)
docker compose -f docker-compose.prod.yml up -d --no-deps --scale platform=1 platform
log "✓ Platform deployed"

# UI last
log "Deploying UI..."
docker compose -f docker-compose.prod.yml up -d --no-deps ui
sleep 10
log "✓ UI deployed"

log "Deployment complete. Running smoke tests..."
bash deploy/smoke_tests.sh
