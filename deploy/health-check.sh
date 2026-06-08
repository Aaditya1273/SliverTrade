#!/bin/bash
# =============================================================================
# SilverTrade AI — Service Health Check
# =============================================================================
# Can be used by monitoring systems (Prometheus, UptimeRobot, Healthchecks.io)
# or as a cron job for periodic health verification.
#
# Usage:
#   bash deploy/health-check.sh              # Basic check
#   bash deploy/health-check.sh --verbose    # Detailed output
#   bash deploy/health-check.sh --json       # JSON output for monitoring
# =============================================================================

set -euo pipefail

# ── Configuration ────────────────────────────────────────────────────────────
DOMAIN="${HOST_SERVER:-http://127.0.0.1:5000}"
TIMEOUT=10          # Seconds per endpoint
MAX_FAILURES=2      # Max failed services before overall failure

# Service health endpoints
SERVICES=(
    "Platform API|$DOMAIN/api/v1/health"
    "Data Fetch|$DOMAIN/data-fetch/api/health"
    "Strategy Engine|$DOMAIN/strategies/api/v1/health"
    "UI Dashboard|$DOMAIN/ui/"
)

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

# ── Check a single endpoint ─────────────────────────────────────────────────
check_endpoint() {
    local NAME="$1"
    local URL="$2"

    local HTTP_CODE
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" --max-time "$TIMEOUT" "$URL" 2>/dev/null || echo "000")

    case "$HTTP_CODE" in
        2[0-9][0-9])
            echo -e "${GREEN}UP${NC} ($HTTP_CODE)"
            return 0
            ;;
        3[0-9][0-9])
            echo -e "${GREEN}UP${NC} (redirect $HTTP_CODE)"
            return 0
            ;;
        000)
            echo -e "${RED}DOWN${NC} (connection failed)"
            return 1
            ;;
        *)
            echo -e "${YELLOW}DEGRADED${NC} ($HTTP_CODE)"
            return 1
            ;;
    esac
}

# ── Run health checks ───────────────────────────────────────────────────────
main() {
    local MODE="${1:-basic}"
    local FAILURES=0
    local RESULTS=()

    echo ""
    echo -e "${CYAN}════════════════════════════════════╗${NC}"
    echo -e "${CYAN}  SilverTrade AI — Health Check    ║${NC}"
    echo -e "${CYAN}╚════════════════════════════════════╝${NC}"
    echo ""

    for SERVICE_INFO in "${SERVICES[@]}"; do
        local NAME="${SERVICE_INFO%%:*}"
        local URL="${SERVICE_INFO#*:}"
        local STATUS

        STATUS=$(check_endpoint "$NAME" "$URL")
        local EXIT_CODE=$?

        if [ "$EXIT_CODE" -ne 0 ]; then
            FAILURES=$((FAILURES + 1))
        fi

        RESULTS+=("$NAME:$STATUS")
        echo -e "  $NAME — $STATUS"
    done

    echo ""

    # ── Summary ──────────────────────────────────────────────────────────
    local TOTAL=${#SERVICES[@]}
    local UP=$((TOTAL - FAILURES))

    if [ "$MODE" = "--json" ]; then
        # JSON output for monitoring systems
        echo "{"
        echo "  \"timestamp\": \"$(date -Iseconds)\","
        echo "  \"total_services\": $TOTAL,"
        echo "  \"healthy\": $UP,"
        echo "  \"unhealthy\": $FAILURES,"
        echo "  \"status\": \"$([ "$FAILURES" -lt "$MAX_FAILURES" ] && echo "healthy" || echo "degraded")\","
        echo "  \"services\": {"
        local FIRST=true
        for RESULT in "${RESULTS[@]}"; do
            local SVC_NAME="${RESULT%% — *}"
            local SVC_STATUS="${RESULT#* — }"
            local SVC_UP="false"
            [[ "$SVC_STATUS" == UP* ]] && SVC_UP="true"
            $FIRST || echo ","
            FIRST=false
            echo -n "    \"$SVC_NAME\": {\"healthy\": $SVC_UP, \"status\": \"$SVC_STATUS\"}"
        done
        echo ""
        echo "  }"
        echo "}"
    else
        if [ "$FAILURES" -eq 0 ]; then
            echo -e "${GREEN}✓ All $TOTAL services healthy${NC}"
        elif [ "$FAILURES" -lt "$MAX_FAILURES" ]; then
            echo -e "${YELLOW}⚠ $UP/$TOTAL services healthy ($FAILURES degraded)${NC}"
        else
            echo -e "${RED}✗ $UP/$TOTAL services healthy ($FAILURES failures)${NC}"
            exit 1
        fi
    fi
}

main "$@"
