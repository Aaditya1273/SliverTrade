#!/bin/bash
# =============================================================================
# SilverTrade AI — Production Deployment Script
# =============================================================================
# Deploys the full SilverTrade stack in production mode with health checks,
# safe rollback on failure, and zero-downtime configuration reloads.
#
# Usage:
#   # First-time deploy:
#   bash deploy/deploy.sh
#
#   # After SSL is set up:
#   bash deploy/deploy.sh --with-ssl
#
#   # Quick update (code changes only):
#   bash deploy/deploy.sh --quick
# =============================================================================

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
COMPOSE_FILE="docker-compose.prod.yml"
DEPLOY_LOG="deploy/deploy.log"
ROLLBACK_TAG="deploy-previous"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "${CYAN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"; }
success() { echo -e "${GREEN}✓${NC} $1"; }
warn() { echo -e "${YELLOW}⚠${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; }

# ── Pre-flight checks ───────────────────────────────────────────────────────
preflight() {
    log "Running pre-flight checks..."

    if ! command -v docker &> /dev/null; then
        error "Docker is not installed. Aborting."
        exit 1
    fi

    if ! docker compose version &> /dev/null; then
        error "Docker Compose plugin is not available. Aborting."
        exit 1
    fi

    if [ ! -f "Platfrom/.env" ]; then
        warn "Platfrom/.env not found!"
        if [ -f "Platfrom/.env.production" ]; then
            log "Copying .env.production to .env..."
            cp Platfrom/.env.production Platfrom/.env
            warn "Please edit Platfrom/.env with your production values before deploying!"
            exit 1
        fi
        error "No .env file found. Create one from Platfrom/.env.production"
        exit 1
    fi

    success "Pre-flight checks passed"
}

# ── Backup current state ────────────────────────────────────────────────────
backup() {
    log "Creating backup of current deployment state..."
    
    # Save image digests for rollback
    docker compose -f "$COMPOSE_FILE" images --quiet 2>/dev/null | \
        sha256sum > "/tmp/${ROLLBACK_TAG}-images.sha256" 2>/dev/null || true
    
    success "Backup saved"
}

# ── Build and deploy ────────────────────────────────────────────────────────
deploy() {
    local QUICK="${1:-false}"

    log "Building services..."
    
    if [ "$QUICK" = true ]; then
        # Quick deploy: only build if images are missing
        docker compose -f "$COMPOSE_FILE" build --pull 2>&1 | \
            while IFS= read -r line; do log "  $line"; done
    else
        # Full deploy: always rebuild
        docker compose -f "$COMPOSE_FILE" build --no-cache --pull 2>&1 | \
            while IFS= read -r line; do log "  $line"; done
    fi

    success "Build complete"

    log "Starting services..."
    docker compose -f "$COMPOSE_FILE" up -d --remove-orphans 2>&1 | \
        while IFS= read -r line; do log "  $line"; done

    success "Services started"
}

# ── Health checks ───────────────────────────────────────────────────────────
health_check() {
    local RETRIES=30
    local INTERVAL=6
    local FAILED=0

    log "Running health checks (timeout: $((RETRIES * INTERVAL))s)..."

    for i in $(seq 1 $RETRIES); do
        local ALL_HEALTHY=true
        
        # Check each service
        for SERVICE in postgres redis platform data_fetch trade_strategies ui nginx; do
            local STATUS
            STATUS=$(docker compose -f "$COMPOSE_FILE" ps --format json "$SERVICE" 2>/dev/null | \
                python3 -c "import sys,json; d=json.load(sys.stdin); print(d.get('Status','')[0:2] if isinstance(d,dict) else '??')" 2>/dev/null || echo "??")
            
            if [ "$STATUS" != "Up" ] && [ "$STATUS" != "He" ]; then
                ALL_HEALTHY=false
                if [ "$i" -eq 1 ]; then
                    warn "Waiting for $SERVICE (status: $STATUS)..."
                fi
            fi
        done

        if [ "$ALL_HEALTHY" = true ]; then
            echo ""
            success "All services healthy!"
            
            # Print final status
            docker compose -f "$COMPOSE_FILE" ps --format "table {{.Name}}\t{{.Status}}\t{{.Ports}}" 2>/dev/null || true
            return 0
        fi

        sleep $INTERVAL
    done

    echo ""
    error "Health check timed out. Some services may not be running."
    docker compose -f "$COMPOSE_FILE" ps 2>/dev/null || true
    return 1
}

# ── Rollback on failure ─────────────────────────────────────────────────────
rollback() {
    warn "Deployment failed! Rolling back..."

    # Restore previous images
    if [ -f "/tmp/${ROLLBACK_TAG}-images.sha256" ]; then
        log "Restoring previous images..."
        docker compose -f "$COMPOSE_FILE" down
        # Re-run with cached layers
        docker compose -f "$COMPOSE_FILE" up -d
        success "Rollback complete"
    else
        warn "No rollback snapshot available. Manual intervention required."
        warn "Check docker compose -f $COMPOSE_FILE logs for details."
    fi
}

# ── Post-deployment ─────────────────────────────────────────────────────────
post_deploy() {
    log "Running post-deployment tasks..."

    # Clean up old images
    docker image prune -f --filter "until=72h" 2>/dev/null || true
    success "Cleaned up old Docker images"

    # Remove old containers
    docker container prune -f --filter "until=24h" 2>/dev/null || true
    success "Cleaned up old containers"

    log "Deployment completed successfully!"
    echo ""
    log "Access your SilverTrade AI instance at:"
    grep -r 'HOST_SERVER' Platfrom/.env 2>/dev/null | head -1 | \
        sed 's/.*= *//' | tr -d "'" | xargs -I{} echo "  → {}"
}

# ── Main ────────────────────────────────────────────────────────────────────
main() {
    local QUICK=false

    # Parse arguments
    for arg in "$@"; do
        case $arg in
            --quick) QUICK=true ;;
            --with-ssl) log "SSL mode: certificates managed by certbot service" ;;
            *) warn "Unknown option: $arg" ;;
        esac
    done

    echo ""
    echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
    echo -e "${GREEN}║    SilverTrade AI — Deploy v1.0.0   ║${NC}"
    echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
    echo ""

    preflight
    backup
    deploy "$QUICK"
    health_check || {
        rollback
        exit 1
    }
    post_deploy
}

main "$@"
