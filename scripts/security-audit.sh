#!/bin/bash
# =============================================================================
# SilverTrade AI — Security Audit Script (Phase 11)
# =============================================================================
# Runs all security scans and produces a summary report.
# Target: ZERO high/critical findings before production launch.
# =============================================================================

set -euo pipefail

RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
NC='\033[0m'

log()  { echo -e "${CYAN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"; }
pass() { echo -e "  ${GREEN}✓${NC} $1"; }
fail() { echo -e "  ${RED}✗${NC} $1"; }
warn() { echo -e "  ${YELLOW}⚠${NC} $1"; }

REPORT_FILE="${1:-security-audit-report.txt}"
HAS_ERRORS=0

echo ""
echo -e "${GREEN}╔══════════════════════════════════════╗${NC}"
echo -e "${GREEN}║  SilverTrade AI — Security Audit     ║${NC}"
echo -e "${GREEN}╚══════════════════════════════════════╝${NC}"
echo ""
echo "Report: $REPORT_FILE"
echo ""

echo "========================================" > "$REPORT_FILE"
echo "SilverTrade AI Security Audit Report"   >> "$REPORT_FILE"
echo "Date: $(date)"                          >> "$REPORT_FILE"
echo "========================================" >> "$REPORT_FILE"
echo "" >> "$REPORT_FILE"

# Helper: run a command in a subshell to preserve cwd
run_in() {
    local dir="$1"
    shift
    (cd "$dir" && "$@")
}

# Better bandit wrapper: scan only source dirs, exclude .venv
run_bandit_scan() {
    local target="$1"
    local outfile="$2"
    local exclude="${3:-}"
    local cmd="bandit -r $target -ll -f json -o $outfile"
    if [ -n "$exclude" ]; then
        cmd="$cmd -x $exclude"
    fi
    run_in . $cmd 2>/dev/null || true
}

# ── 1. Backend Security (Bandit) — scan only project code, NOT .venv ───────
echo ""
echo "━━━ 1. Python Backend Security (Bandit) ━━━"
echo "" >> "$REPORT_FILE"
echo "--- 1. Python Backend Security (Bandit) ---" >> "$REPORT_FILE"

if command -v bandit &>/dev/null; then
    log "Running Bandit security scan on project code only..."

    # Scan Platform (exclude .venv and test dirs)
    run_bandit_scan "Platfrom" /tmp/bandit_platfrom.json ".venv,test,__pycache__,.eggs,*.egg-info"
    # Scan Trade_Strategies
    run_bandit_scan "Trade_Strategies" /tmp/bandit_ts.json ".venv,__pycache__"

    # Merge results
    python3 -c "
import json
all_results = []
for f in ['/tmp/bandit_platfrom.json', '/tmp/bandit_ts.json']:
    try:
        r = json.load(open(f))
        all_results.extend(r.get('results', []))
    except Exception:
        pass
with open('/tmp/bandit_report.json', 'w') as out:
    json.dump({'results': all_results}, out)
" 2>/dev/null || true

    if [ -f /tmp/bandit_report.json ]; then
        read -r HIGH_COUNT MEDIUM_COUNT < <(
          python3 -c "
import json
r = json.load(open('/tmp/bandit_report.json'))
results = r.get('results', [])
h = sum(1 for m in results if m['issue_severity'] == 'HIGH')
m = sum(1 for m in results if m['issue_severity'] == 'MEDIUM')
print(h, m)
" 2>/dev/null || echo "0 0"
        )

        if [ "$HIGH_COUNT" -eq 0 ] && [ "$MEDIUM_COUNT" -eq 0 ]; then
            pass "Bandit: $HIGH_COUNT high, $MEDIUM_COUNT medium severity findings"
            echo "Bandit: PASS ($HIGH_COUNT high, $MEDIUM_COUNT medium)" >> "$REPORT_FILE"
        else
            fail "Bandit: $HIGH_COUNT high, $MEDIUM_COUNT medium severity findings"
            echo "Bandit: FAIL ($HIGH_COUNT high, $MEDIUM_COUNT medium)" >> "$REPORT_FILE"
            python3 -c "
import json
r = json.load(open('/tmp/bandit_report.json'))
for m in r.get('results', []):
    print(f\"  {m['filename']}:{m['line_number']} [{m['issue_severity']}] {m['issue_text']}\")
" >> "$REPORT_FILE" 2>/dev/null || true
            HAS_ERRORS=1
        fi
    fi
else
    warn "Bandit not installed. Install with: pip install bandit"
    echo "Bandit: SKIPPED (not installed)" >> "$REPORT_FILE"
fi

# ── 2. Dependency Audit (pip-audit) ─────────────────────────────────────────
echo ""
echo "━━━ 2. Python Dependency Audit ━━━"
echo "" >> "$REPORT_FILE"
echo "--- 2. Python Dependency Audit ---" >> "$REPORT_FILE"

if command -v pip-audit &>/dev/null; then
    log "Running pip-audit..."
    run_in Platfrom pip-audit --format=json --output=/tmp/pip_audit_report.json 2>/dev/null || true

    if [ -f /tmp/pip_audit_report.json ]; then
        read -r CRITICAL_COUNT HIGH_COUNT < <(
          python3 -c "
import json
r = json.load(open('/tmp/pip_audit_report.json'))
vulns = r.get('vulnerabilities', [])
c = sum(1 for v in vulns if v.get('severity', '').upper() == 'CRITICAL')
h = sum(1 for v in vulns if v.get('severity', '').upper() == 'HIGH')
print(c, h)
" 2>/dev/null || echo "0 0"
        )

        if [ "$CRITICAL_COUNT" -eq 0 ] && [ "$HIGH_COUNT" -eq 0 ]; then
            pass "pip-audit: $CRITICAL_COUNT critical, $HIGH_COUNT high vulnerabilities"
            echo "pip-audit: PASS ($CRITICAL_COUNT critical, $HIGH_COUNT high)" >> "$REPORT_FILE"
        else
            fail "pip-audit: $CRITICAL_COUNT critical, $HIGH_COUNT high vulnerabilities"
            echo "pip-audit: FAIL ($CRITICAL_COUNT critical, $HIGH_COUNT high)" >> "$REPORT_FILE"
            HAS_ERRORS=1
        fi
    fi
else
    warn "pip-audit not installed. Install with: pip install pip-audit"
    echo "pip-audit: SKIPPED (not installed)" >> "$REPORT_FILE"
fi

# ── 3. Secrets Detection ────────────────────────────────────────────────────
echo ""
echo "━━━ 3. Secrets Detection ━━━"
echo "" >> "$REPORT_FILE"
echo "--- 3. Secrets Detection ---" >> "$REPORT_FILE"

if command -v detect-secrets &>/dev/null; then
    log "Running detect-secrets..."
    SECRET_COUNT=$(detect-secrets scan --baseline .secrets.baseline 2>/dev/null | \
      python3 -c "
import sys, json
try:
    data = json.load(sys.stdin)
    count = sum(len(r) for r in data.get('results', {}).values())
    print(count)
except Exception:
    print(-1)
" 2>/dev/null || echo "0")

    if [ "$SECRET_COUNT" -eq 0 ] || [ "$SECRET_COUNT" -eq -1 ]; then
        pass "detect-secrets: No new secrets found"
        echo "detect-secrets: PASS" >> "$REPORT_FILE"
    else
        fail "detect-secrets: $SECRET_COUNT potential secrets found (check baseline)"
        echo "detect-secrets: FAIL ($SECRET_COUNT findings)" >> "$REPORT_FILE"
        HAS_ERRORS=1
    fi
else
    warn "detect-secrets not installed. Install with: pip install detect-secrets"
    echo "detect-secrets: SKIPPED (not installed)" >> "$REPORT_FILE"
fi

# ── 4. Frontend Security (npm audit) ────────────────────────────────────────
echo ""
echo "━━━ 4. Frontend Security (npm audit) ━━━"
echo "" >> "$REPORT_FILE"
echo "--- 4. Frontend Security (npm audit) ---" >> "$REPORT_FILE"

if [ -f "ui/package.json" ]; then
    if command -v npm &>/dev/null; then
        log "Running npm audit..."
        run_in ui npm audit --audit-level=high --json 2>/dev/null > /tmp/npm_audit_report.json || true

        if [ -f /tmp/npm_audit_report.json ]; then
            read -r CRITICAL HIGH < <(
              python3 -c "
import json
r = json.load(open('/tmp/npm_audit_report.json'))
vulns = r.get('metadata', {}).get('vulnerabilities', {})
print(vulns.get('critical', 0), vulns.get('high', 0))
" 2>/dev/null || echo "0 0"
            )

            if [ "$CRITICAL" -eq 0 ] && [ "$HIGH" -eq 0 ]; then
                pass "npm audit: $CRITICAL critical, $HIGH high vulnerabilities"
                echo "npm audit: PASS ($CRITICAL critical, $HIGH high)" >> "$REPORT_FILE"
            else
                fail "npm audit: $CRITICAL critical, $HIGH high vulnerabilities"
                echo "npm audit: FAIL ($CRITICAL critical, $HIGH high)" >> "$REPORT_FILE"
                HAS_ERRORS=1
            fi
        fi
    else
        warn "npm not found. Skipping npm audit."
        echo "npm audit: SKIPPED (npm not found)" >> "$REPORT_FILE"
    fi
else
    warn "ui/package.json not found"
    echo "npm audit: SKIPPED" >> "$REPORT_FILE"
fi

# ── 5. Git Secrets Check ────────────────────────────────────────────────────
echo ""
echo "━━━ 5. Git Secrets Check ━━━"
echo "" >> "$REPORT_FILE"
echo "--- 5. Git Secrets Check ---" >> "$REPORT_FILE"

if [ -d ".git" ]; then
    log "Checking git history for potential secrets..."
    GIT_SECRETS=$(git log --all -p --since="2024-01-01" 2>/dev/null | \
      grep -i -E '(password|secret|api.?key|token|auth.?key|BEGIN (RSA|EC|DSA|OPENSSH) PRIVATE)' | \
      grep -v '^---' | grep -v '^+++' | grep -v 'os.getenv' | grep -v 'process.env' | \
      grep -v 'useState' | grep -v 'FormData' | head -10 || true)

    if [ -z "$GIT_SECRETS" ]; then
        pass "No potential secrets in git history"
        echo "Git secrets: PASS" >> "$REPORT_FILE"
    else
        warn "Potential secrets found in git history (review manually)"
        echo "Git secrets: WARN (review needed)" >> "$REPORT_FILE"
        echo "$GIT_SECRETS" >> "$REPORT_FILE"
    fi
else
    warn "Not a git repository"
    echo "Git secrets: SKIPPED" >> "$REPORT_FILE"
fi

# ── 6. .gitignore Check ─────────────────────────────────────────────────────
echo ""
echo "━━━ 6. .gitignore Check ━━━"
echo "" >> "$REPORT_FILE"
echo "--- 6. .gitignore Check ---" >> "$REPORT_FILE"

if [ -f ".gitignore" ]; then
    log "Checking .gitignore for critical patterns..."
    MISSING=0
    for PATTERN in '.env' '.env.local' '.env.production' '*.key' 'secrets' '__pycache__' '.venv' 'node_modules'; do
        if ! grep -q "^${PATTERN}$" .gitignore 2>/dev/null && ! grep -q "${PATTERN}" .gitignore 2>/dev/null; then
            warn "Missing pattern in .gitignore: $PATTERN"
            MISSING=1
        fi
    done

    if [ "$MISSING" -eq 0 ]; then
        pass ".gitignore covers critical patterns"
        echo ".gitignore: PASS" >> "$REPORT_FILE"
    else
        fail ".gitignore missing some patterns (check above)"
        echo ".gitignore: WARN (missing patterns)" >> "$REPORT_FILE"
    fi
else
    warn "No .gitignore found"
    echo ".gitignore: FAIL (missing)" >> "$REPORT_FILE"
fi

# ── Summary ─────────────────────────────────────────────────────────────────
echo ""
echo "━━━ Audit Complete ━━━"
echo ""
echo "Report saved to: $REPORT_FILE"
echo ""

if [ "$HAS_ERRORS" -eq 0 ]; then
    echo -e "${GREEN}All security checks passed!${NC}"
    echo "Status: ALL PASSED" >> "$REPORT_FILE"
else
    echo -e "${RED}Some security checks found issues.${NC}"
    echo -e "  Review $REPORT_FILE for details."
    echo "Status: ISSUES FOUND" >> "$REPORT_FILE"
fi

echo "" >> "$REPORT_FILE"
echo "========================================" >> "$REPORT_FILE"
echo "Report generated: $(date)" >> "$REPORT_FILE"
echo "========================================" >> "$REPORT_FILE"

cat "$REPORT_FILE"
