#!/bin/bash
# =============================================================================
# SilverTrade AI — Smoke Tests (Phase 9)
# =============================================================================
# Basic smoke tests after deployment.
# Tests all core services against their actual API endpoints.
# =============================================================================

set -euo pipefail

BASE="${HOST_SERVER:-http://localhost:5000}"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log()   { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"; }
error() { echo -e "${RED}✗${NC} $1"; }

PASS=0
FAIL=0

check() {
    local name="$1"
    local status="$2"
    if [ "$status" = "pass" ]; then
        log "✅ $name"
        PASS=$((PASS + 1))
    else
        error "$name — $3"
        FAIL=$((FAIL + 1))
    fi
}

log "Running smoke tests against: $BASE"
echo ""

# ── 1. Platform health ──────────────────────────────────────────────
HTTP=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/health/status" 2>&1)
HEALTH_BODY=$(curl -s "$BASE/health/status" 2>&1)
if [ "$HTTP" = "200" ] && echo "$HEALTH_BODY" | grep -q '"status":"pass"'; then
    check "Platform health status" "pass" ""
else
    check "Platform health status" "fail" "HTTP $HTTP — expected 200 with pass status"
fi

# ── 2. Detailed health check (may return 503 if DB degraded, but endpoint must respond) ──
HTTP=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/health/check" 2>&1)
if [ "$HTTP" = "200" ] || [ "$HTTP" = "503" ]; then
    check "Detailed health endpoint responds" "pass" "HTTP $HTTP"
else
    check "Detailed health endpoint responds" "fail" "HTTP $HTTP — unexpected status"
fi

# ── 3. Signals API ──────────────────────────────────────────────────
HTTP=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/api/v1/signals/" 2>&1)
BODY=$(curl -s "$BASE/api/v1/signals/" 2>&1)
if [ "$HTTP" = "200" ] && echo "$BODY" | grep -q '"status":"success"'; then
    check "Signals API" "pass" ""
else
    check "Signals API" "fail" "HTTP $HTTP — expected 200 with success status"
fi

# ── 5. API config endpoint ──────────────────────────────────────────
HTTP=$(curl -s -o /dev/null -w '%{http_code}' "$BASE/api/config/host" 2>&1)
if [ "$HTTP" = "200" ]; then
    check "API config endpoint" "pass" ""
else
    check "API config endpoint" "fail" "HTTP $HTTP — expected 200"
fi

# ── 6. Auth endpoint exists ─────────────────────────────────────────
# POST with empty body returns either 400 (CSRF) or 400 (missing data) — both prove the endpoint works
HTTP=$(curl -s -o /dev/null -w '%{http_code}' -X POST "$BASE/auth/login" \
    -H "Content-Type: application/json" -d '{}' 2>&1)
if [ "$HTTP" = "400" ] || [ "$HTTP" = "405" ]; then
    check "Auth endpoint" "pass" ""
else
    check "Auth endpoint" "fail" "HTTP $HTTP — expected 4xx (auth requires form data or session)"
fi

# ── 7. Service identity check ────────────────────────────────────────
# Verify the health response contains the expected serviceId: silvertrade
if echo "$HEALTH_BODY" | grep -qi "silvertrade"; then
    check "Service identity in health response" "pass" ""
else
    check "Service identity in health response" "fail" "Service identity not found"
fi

echo ""
log "Results: $PASS passed, $FAIL failed"

if [ "$FAIL" -gt 0 ]; then
    error "Some smoke tests failed."
    exit 1
fi

log "All smoke tests passed."
