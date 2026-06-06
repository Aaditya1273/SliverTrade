#!/bin/bash
# =============================================================================
# SilverTrade AI — Automated Security Audit (Phase 11)
# =============================================================================
# Runs all automated security scans and generates reports
# =============================================================================

set -euo pipefail

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"; }
error() { echo -e "${RED}ERROR:${NC} $1"; }
warn() { echo -e "${YELLOW}WARNING:${NC} $1"; }

REPORT_DIR="security_reports"
mkdir -p "$REPORT_DIR"

log "Starting automated security audit..."

# 1. Backend Security - Bandit
log "Running Bandit on Platform..."
cd Platfrom
if command -v bandit &> /dev/null; then
    uv run bandit -r . -ll -x .venv,test,__pycache__ -f json -o "../$REPORT_DIR/bandit_report.json" || true
    uv run bandit -r . -ll -x .venv,test,__pycache__ -f txt -o "../$REPORT_DIR/bandit_report.txt" || true
    log "✓ Bandit scan complete"
else
    warn "Bandit not installed. Run: pip install bandit"
fi

cd ..

# 2. Dependency Vulnerabilities - pip-audit
log "Running pip-audit on Platform..."
cd Platfrom
if command -v pip-audit &> /dev/null; then
    uv run pip-audit --format=json --output="../$REPORT_DIR/pip_audit_report.json" || true
    uv run pip-audit --output="../$REPORT_DIR/pip_audit_report.txt" || true
    log "✓ pip-audit scan complete"
else
    warn "pip-audit not installed. Run: pip install pip-audit"
fi

cd ..

# 3. Dependency Vulnerabilities - Trade Strategies
log "Running pip-audit on Trade Strategies..."
cd Trade_Strategies
if command -v pip-audit &> /dev/null; then
    uv run pip-audit --format=json --output="../$REPORT_DIR/pip_audit_strategies.json" || true
    uv run pip-audit --output="../$REPORT_DIR/pip_audit_strategies.txt" || true
    log "✓ pip-audit scan complete"
else
    warn "pip-audit not installed"
fi

cd ..

# 4. Secrets Detection - detect-secrets
log "Running detect-secrets..."
if command -v detect-secrets &> /dev/null; then
    if [ -f ".secrets.baseline" ]; then
        detect-secrets scan --baseline .secrets.baseline > "$REPORT_DIR/detect_secrets_report.txt" 2>&1 || true
        log "✓ detect-secrets scan complete"
    else
        warn "No .secrets.baseline found. Run: detect-secrets scan > .secrets.baseline"
    fi
else
    warn "detect-secrets not installed. Run: pip install detect-secrets"
fi

# 5. Frontend Security - npm audit
log "Running npm audit on UI..."
cd ui
if command -v npm &> /dev/null; then
    npm audit --audit-level=high --json > "../$REPORT_DIR/npm_audit.json" 2>&1 || true
    npm audit --audit-level=high > "../$REPORT_DIR/npm_audit.txt" 2>&1 || true
    log "✓ npm audit complete"
else
    warn "npm not available"
fi

cd ..

# 6. Docker Image Security - Trivy
log "Running Trivy on Docker images..."
if command -v trivy &> /dev/null; then
    trivy image silvertrade-platform:latest --severity HIGH,CRITICAL --format json --output "$REPORT_DIR/trivy_platform.json" 2>&1 || true
    trivy image silvertrade-ui:latest --severity HIGH,CRITICAL --format json --output "$REPORT_DIR/trivy_ui.json" 2>&1 || true
    trivy image silvertrade-trade-strategies:latest --severity HIGH,CRITICAL --format json --output "$REPORT_DIR/trivy_strategies.json" 2>&1 || true
    log "✓ Trivy scan complete"
else
    warn "Trivy not installed. Run: https://aquasecurity.github.io/trivy/"
fi

log "Security audit complete. Reports in: $REPORT_DIR/"
log "Review the reports and resolve all Critical/High findings before launch."
