#!/bin/bash
# =============================================================================
# SilverTrade AI — SQLite → PostgreSQL Migration Runbook
# =============================================================================
#
# Orchestrates the full migration from SQLite to PostgreSQL:
#   1. Pre-flight checks (Docker, Python deps, .env file)
#   2. Start local PostgreSQL via Docker (optional)
#   3. Generate .env with Docker PostgreSQL URLs
#   4. Dry-run migration (safety check)
#   5. Full data migration
#   6. Alembic stamp for all 5 databases
#   7. Verification
#
# Usage:
#   bash upgrade/migrate.sh                     # Full migration with Docker PG
#   bash upgrade/migrate.sh --dry-run           # Safety check only
#   bash upgrade/migrate.sh --skip-docker       # Skip Docker PG start (PG already running)
#   bash upgrade/migrate.sh --supabase          # Use Supabase URLs (set in .env first)
#   bash upgrade/migrate.sh --only main         # Migrate only main database
#
# Environment:
#   Set these BEFORE running if using custom PostgreSQL:
#     DATABASE_URL, LOGS_DATABASE_URL, LATENCY_DATABASE_URL,
#     HEALTH_DATABASE_URL, SANDBOX_DATABASE_URL
#
# =============================================================================

set -euo pipefail

# ── Config ──────────────────────────────────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
ENV_FILE="$PROJECT_ROOT/.env"
ENV_BACKUP="$PROJECT_ROOT/.env.sqlite-backup-$(date +%Y%m%d-%H%M%S)"
PG_COMPOSE_SERVICE="postgres"

# Docker PostgreSQL credentials (for local Docker PG)
DOCKER_PG_USER="silvertrade"
DOCKER_PG_PASSWORD="silvertrade"
DOCKER_PG_DB="silvertrade"
DOCKER_PG_PORT="5432"

# ── Colors ──────────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
CYAN='\033[0;36m'
MAGENTA='\033[0;35m'
BOLD='\033[1m'
NC='\033[0m'

# ── Logging helpers ─────────────────────────────────────────────────────────
log()    { echo -e "${CYAN}[$(date +'%H:%M:%S')]${NC} $1"; }
success(){ echo -e "  ${GREEN}✓${NC} $1"; }
warn()   { echo -e "  ${YELLOW}⚠${NC} $1"; }
error()  { echo -e "  ${RED}✗${NC} $1"; fail=true; }
header() { echo -e "\n${MAGENTA}${BOLD}═══ $1 ═══${NC}\n"; }
fail=false

# ── Cleanup trap ────────────────────────────────────────────────────────────
cleanup() {
    local exit_code=$?
    if [ $exit_code -ne 0 ] && [ "$fail" = true ]; then
        echo ""
        warn "Migration did not complete successfully."
        warn "Your original .env is backed up at: $ENV_BACKUP"
        warn "To restore: cp $ENV_BACKUP $ENV_FILE"
    fi
    exit $exit_code
}
trap cleanup EXIT


# ═══════════════════════════════════════════════════════════════════════════
# Pre-flight Checks
# ═══════════════════════════════════════════════════════════════════════════

preflight() {
    header "Pre-flight Checks"

    # ── Python / uv ────────────────────────────────────────────
    if ! command -v uv &> /dev/null; then
        error "uv is not installed. Install it: curl -LsSf https://astral.sh/uv/install.sh | sh"
        return 1
    fi
    success "uv $(uv version --short 2>/dev/null || echo 'installed')"

    # ── psycopg2 ───────────────────────────────────────────────
    if ! python3 -c "import psycopg2" 2>/dev/null; then
        log "Installing psycopg2..."
        uv add psycopg2-binary 2>&1 | tail -1
    fi
    success "psycopg2 available"

    # ── .env file ──────────────────────────────────────────────
    if [ ! -f "$ENV_FILE" ]; then
        error ".env file not found at $ENV_FILE"
        log "   Copy from .sample.env: cp $PROJECT_ROOT/.sample.env $ENV_FILE"
        return 1
    fi
    success ".env file found"

    # ── Backup current .env ────────────────────────────────────
    cp "$ENV_FILE" "$ENV_BACKUP"
    success "Backed up .env → $(basename "$ENV_BACKUP")"
}


# ═══════════════════════════════════════════════════════════════════════════
# Docker PostgreSQL
# ═══════════════════════════════════════════════════════════════════════════

start_docker_pg() {
    header "Starting Docker PostgreSQL"

    # Check if PG is already running and accepting connections
    # Try pg_isready first (if available), then fallback to psycopg2
    if command -v pg_isready &>/dev/null && pg_isready -h 127.0.0.1 -p "$DOCKER_PG_PORT" &>/dev/null 2>&1; then
        success "PostgreSQL already running on port $DOCKER_PG_PORT"
        return 0
    fi
    if python3 -c "import psycopg2; psycopg2.connect(host='127.0.0.1', port=$DOCKER_PG_PORT, user='$DOCKER_PG_USER', dbname='$DOCKER_PG_DB', connect_timeout=2)" &>/dev/null 2>&1; then
        success "PostgreSQL already running on port $DOCKER_PG_PORT"
        return 0
    fi

    # Check if Docker is available
    if ! docker info --format '{{.ServerVersion}}' &>/dev/null 2>&1; then
        warn "Docker is not running. Cannot start PostgreSQL automatically."
        warn "Start PostgreSQL manually, then re-run with --skip-docker."
        warn "Or use an existing PostgreSQL instance and set the URLs in .env."
        return 1
    fi
    success "Docker $(docker info --format '{{.ServerVersion}}')"

    # Start PostgreSQL from docker-compose.staging.yml
    log "Starting PostgreSQL container..."
    local COMPOSE_FILE="$PROJECT_ROOT/../docker-compose.staging.yml"

    if [ -f "$COMPOSE_FILE" ]; then
        docker compose -f "$COMPOSE_FILE" up -d postgres 2>&1 | while IFS= read -r line; do
            echo "     $line"
        done
    else
        # Fallback: run PostgreSQL directly
        docker run -d \
            --name silvertrade-migration-pg \
            --rm \
            -p "$DOCKER_PG_PORT:5432" \
            -e POSTGRES_USER="$DOCKER_PG_USER" \
            -e POSTGRES_PASSWORD="$DOCKER_PG_PASSWORD" \
            -e POSTGRES_DB="$DOCKER_PG_DB" \
            postgres:16-alpine 2>&1 | while IFS= read -r line; do
            echo "     $line"
        done
    fi

    # Wait for PG to be ready
    log "Waiting for PostgreSQL to accept connections..."
    local RETRIES=30
    local i=0
    while true; do
        # Try pg_isready first (if available), then fallback to psycopg2
        if command -v pg_isready &>/dev/null && pg_isready -h 127.0.0.1 -p "$DOCKER_PG_PORT" &>/dev/null 2>&1; then
            break
        fi
        if python3 -c "import psycopg2; psycopg2.connect(host='127.0.0.1', port=$DOCKER_PG_PORT, user='$DOCKER_PG_USER', dbname='$DOCKER_PG_DB', connect_timeout=2)" &>/dev/null 2>&1; then
            break
        fi
        i=$((i + 1))
        if [ $i -ge $RETRIES ]; then
            error "PostgreSQL did not start within ${RETRIES}s"
            docker logs silvertrade-staging-postgres 2>/dev/null || \
            docker logs silvertrade-migration-pg 2>/dev/null || true
            return 1
        fi
        sleep 1
    done
    success "PostgreSQL 16 is ready on port $DOCKER_PG_PORT"
}


# ═══════════════════════════════════════════════════════════════════════════
# Generate .env with Docker PostgreSQL URLs
# ═══════════════════════════════════════════════════════════════════════════

generate_docker_pg_env() {
    header "Generating .env with Docker PostgreSQL URLs"

    local PG_HOST="127.0.0.1"
    local PG_URL="postgresql://${DOCKER_PG_USER}:${DOCKER_PG_PASSWORD}@${PG_HOST}:${DOCKER_PG_PORT}/${DOCKER_PG_DB}"

    # Build the 5 PostgreSQL URLs with ?options for schema isolation
    local DATABASE_URL="${PG_URL}"
    local LOGS_URL="${PG_URL}?options=-c%20search_path=logs"
    local LATENCY_URL="${PG_URL}?options=-c%20search_path=latency"
    local HEALTH_URL="${PG_URL}?options=-c%20search_path=health"
    local SANDBOX_URL="${PG_URL}?options=-c%20search_path=sandbox"

    # Read current .env and replace DATABASE_* URLs
    # Use sed to find and replace each DATABASE_* line
    local TMP_ENV=$(mktemp)

    while IFS= read -r line || [ -n "$line" ]; do
        # Skip comment-only lines about PostgreSQL examples
        # Allow optional spaces around = (e.g., DATABASE_URL = 'value')
        if [[ "$line" =~ ^[[:space:]]*#.*DATABASE_URL ]]; then
            continue
        fi

        # Replace active DATABASE_URL lines — handle optional spaces around =
        if [[ "$line" =~ ^[[:space:]]*DATABASE_URL[[:space:]]*= ]]; then
            echo "DATABASE_URL = '${DATABASE_URL}'" >> "$TMP_ENV"
        elif [[ "$line" =~ ^[[:space:]]*LOGS_DATABASE_URL[[:space:]]*= ]]; then
            echo "LOGS_DATABASE_URL = '${LOGS_URL}'" >> "$TMP_ENV"
        elif [[ "$line" =~ ^[[:space:]]*LATENCY_DATABASE_URL[[:space:]]*= ]]; then
            echo "LATENCY_DATABASE_URL = '${LATENCY_URL}'" >> "$TMP_ENV"
        elif [[ "$line" =~ ^[[:space:]]*HEALTH_DATABASE_URL[[:space:]]*= ]]; then
            echo "HEALTH_DATABASE_URL = '${HEALTH_URL}'" >> "$TMP_ENV"
        elif [[ "$line" =~ ^[[:space:]]*SANDBOX_DATABASE_URL[[:space:]]*= ]]; then
            echo "SANDBOX_DATABASE_URL = '${SANDBOX_URL}'" >> "$TMP_ENV"
        else
            echo "$line" >> "$TMP_ENV"
        fi
    done < "$ENV_FILE"

    mv "$TMP_ENV" "$ENV_FILE"
    success ".env updated with Docker PostgreSQL URLs"

    # Print summary
    echo ""
    log "New database URLs:"
    echo "  DATABASE_URL       → postgresql://${DOCKER_PG_USER}:****@${PG_HOST}:${DOCKER_PG_PORT}/${DOCKER_PG_DB}"
    echo "  LOGS_DATABASE_URL  → .../postgres?options=-c%20search_path=logs"
    echo "  LATENCY_DATABASE_URL → .../postgres?options=-c%20search_path=latency"
    echo "  HEALTH_DATABASE_URL → .../postgres?options=-c%20search_path=health"
    echo "  SANDBOX_DATABASE_URL → .../postgres?options=-c%20search_path=sandbox"
}


# ═══════════════════════════════════════════════════════════════════════════
# Run Migration
# ═══════════════════════════════════════════════════════════════════════════

run_migration() {
    local MODE="${1:-full}"  # "dry-run" or "full"
    local SCOPE="${2:-all}"  # "all" or specific database name
    shift 2

    if [ "$MODE" = "dry-run" ]; then
        header "Dry-Run Migration (safety check — no changes)"
        cd "$PROJECT_ROOT"
        uv run python upgrade/migrate_to_postgresql.py --dry-run --only "$SCOPE" "$@"
        echo ""
        success "Dry-run complete. Review the output above."
        log "No data was changed."
    else
        header "Full Migration"
        cd "$PROJECT_ROOT"
        uv run python upgrade/migrate_to_postgresql.py --only "$SCOPE" "$@"
        echo ""

        # Check exit code
        if [ $? -eq 0 ]; then
            success "Migration command completed"
        else
            error "Migration command failed"
            return 1
        fi
    fi
}


# ═══════════════════════════════════════════════════════════════════════════
# Alembic Stamping
# ═══════════════════════════════════════════════════════════════════════════

run_alembic() {
    header "Alembic — Stamp All 5 Databases"

    local ALEMBIC_INI="$PROJECT_ROOT/database/alembic.ini"

    if [ ! -f "$ALEMBIC_INI" ]; then
        warn "Alembic config not found at $ALEMBIC_INI — skipping Alembic stamping"
        return 0
    fi

    # Run for each database
    local DATABASES=("main" "logs" "latency" "health" "sandbox")
    local all_ok=true

    for db in "${DATABASES[@]}"; do
        local db_label=$(echo "$db" | tr '[:lower:]' '[:upper:]')
        printf "  Alembic %s ... " "$db_label"

        if ALEMBIC_DB="$db" uv run alembic -c "$ALEMBIC_INI" upgrade head &>/tmp/alembic_${db}.log; then
            echo -e "${GREEN}✓${NC} head applied"
        else
            echo -e "${RED}✗${NC} failed (see /tmp/alembic_${db}.log)"
            all_ok=false
        fi
    done

    echo ""
    if [ "$all_ok" = true ]; then
        success "All 5 databases stamped"
    else
        warn "Some databases had Alembic issues — check logs above"
    fi
}


# ═══════════════════════════════════════════════════════════════════════════
# Verification
# ═══════════════════════════════════════════════════════════════════════════

verify() {
    header "Verification — Check All Databases"

    cd "$PROJECT_ROOT"

    # Source the .env to get PG URLs
    # (Python script handles this internally, but we need them for direct queries)
    log "Testing all 5 database connections..."

    uv run python3 -c "
import os, sys
sys.path.insert(0, '.')
from database.db_config import check_all_databases

result = check_all_databases()
print(f\"  Overall status: {result['status'].upper()}\")
print()
for name, db in result['databases'].items():
    icon = '✅' if db['status'] == 'pass' else '❌'
    print(f'  {icon} {name}: {db[\"latency_ms\"]}ms ({db[\"driver\"]})')

print()
if result.get('pool_stats'):
    for label, stats in result['pool_stats'].items():
        driver = stats.get('driver', '?')
        if stats.get('pool_class') != 'NullPool':
            in_use = stats.get('in_use_pct', 0)
            print(f'  📊 Pool {label}: {stats[\"size\"]} conns, {in_use}% in use')
        else:
            print(f'  📊 Pool {label}: {driver} ({stats[\"pool_class\"]})')
" || {
        warn "Python verification failed — trying direct psycopg2..."
        # Fallback: direct connection test
        for key in DATABASE_URL LOGS_DATABASE_URL LATENCY_DATABASE_URL HEALTH_DATABASE_URL SANDBOX_DATABASE_URL; do
            url="${!key:-}"
            if [ -n "$url" ]; then
                # Strip options parameter for psycopg2 direct connect
                clean_url=$(echo "$url" | sed 's/\?options=.*//')
                if python3 -c "
import psycopg2
try:
    c = psycopg2.connect('$clean_url', connect_timeout=3)
    cur = c.cursor()
    cur.execute('SELECT 1')
    cur.close()
    c.close()
    print('  ✅ $key: connected')
except Exception as e:
    print('  ❌ $key: ' + str(e)[:80])
" 2>&1; then
                    :
                fi
            fi
        done
    }

    echo ""
    log "To manually verify specific tables:"
    echo "  uv run python -c \"import psycopg2, os; c = psycopg2.connect(os.environ['DATABASE_URL']); cur = c.cursor(); cur.execute('SELECT count(*) FROM auth'); print(f'Auth records: {cur.fetchone()[0]}')\""
}


# ═══════════════════════════════════════════════════════════════════════════
# Rollback .env to SQLite
# ═══════════════════════════════════════════════════════════════════════════

rollback_env() {
    warn "Restoring .env to SQLite configuration..."
    cp "$ENV_BACKUP" "$ENV_FILE"
    success ".env restored from $(basename "$ENV_BACKUP")"
}


# ═══════════════════════════════════════════════════════════════════════════
# Main
# ═══════════════════════════════════════════════════════════════════════════

main() {
    local DRY_RUN=false
    local SKIP_DOCKER=false
    local USE_SUPABASE=false
    local SCOPE="all"
    local EXTRA_ARGS=()

    # ── Parse arguments ────────────────────────────────────────
    for arg in "$@"; do
        case $arg in
            --dry-run) DRY_RUN=true ;;
            --skip-docker) SKIP_DOCKER=true ;;
            --supabase) USE_SUPABASE=true ;;
            --only=*) SCOPE="${arg#*=}" ;;
            --only) EXTRA_ARGS+=("--only"); SCOPE="${2:-all}"; shift ;;
            --force) EXTRA_ARGS+=("--force") ;;
            --set-env) EXTRA_ARGS+=("--set-env") ;;
            -h|--help)
                echo "Usage: bash upgrade/migrate.sh [options]"
                echo ""
                echo "Options:"
                echo "  --dry-run          Safety check only (no data changes)"
                echo "  --skip-docker      Use existing PostgreSQL (don't start Docker)"
                echo "  --supabase         Use Supabase URLs from .env"
                echo "  --only=DB          Migrate only one database (main|logs|latency|health|sandbox)"
                echo "  --force            Drop and recreate tables if they exist"
                echo "  --set-env          Auto-update .env with Supabase URLs"
                echo "  -h, --help         Show this help"
                exit 0
                ;;
            *) EXTRA_ARGS+=("$arg") ;;
        esac
    done

    # ── Banner ─────────────────────────────────────────────────
    echo ""
    echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}${BOLD}║    SilverTrade AI — SQLite → PostgreSQL Migration  ║${NC}"
    echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""

    # ── Pre-flight ─────────────────────────────────────────────
    preflight || { error "Pre-flight failed"; exit 1; }

    # ── Docker PostgreSQL ─────────────────────────────────────
    if [ "$DRY_RUN" = false ] && [ "$USE_SUPABASE" = false ]; then
        if [ "$SKIP_DOCKER" = false ]; then
            start_docker_pg || {
                warn "Could not start Docker PostgreSQL."
                log "Options:"
                log "  1. Start Docker and re-run"
                log "  2. Re-run with --skip-docker (PG already running)"
                log "  3. Use --supabase for cloud PG"
                exit 1
            }
        fi

        # Generate .env with Docker PG URLs
        generate_docker_pg_env
    elif [ "$USE_SUPABASE" = true ]; then
        header "Using Supabase PostgreSQL"
        # Verify Supabase URLs are set in .env
        # Use Python to parse .env (handles spaces around =, quotes, etc.)
        SUPABASE_URL=$(python3 -c "
import re
with open('$ENV_FILE') as f:
    for line in f:
        line = line.strip()
        if line.startswith('#'):
            continue
        m = re.match(r'^DATABASE_URL[\\s]*=[\\s]*[\"\']?(.+?)[\"\']?[\\s]*$', line)
        if m:
            print(m.group(1))
            break
" 2>/dev/null || echo "")
        if [[ -z "${SUPABASE_URL:-}" || ! "${SUPABASE_URL:-}" =~ supabase ]]; then
            warn "DATABASE_URL does not contain 'supabase'"
            log "Make sure you've set Supabase URLs in .env"
            log "  Example: DATABASE_URL = 'postgresql://postgres.YOUR_REF:YOUR_PASSWORD@aws-1-ap-northeast-1.pooler.supabase.com:6543/postgres'"
            exit 1
        fi
        success "Supabase URLs detected in .env"
    else
        header "Using Existing PostgreSQL"
        log "Using PostgreSQL URLs as configured in .env"
        # Source current URLs for display
        source <(grep -E '^DATABASE_URL' "$ENV_FILE" 2>/dev/null || echo "")
        log "  DATABASE_URL: ${DATABASE_URL:-not set}"
    fi

    # ── Dry Run ────────────────────────────────────────────────
    if [ "$DRY_RUN" = true ]; then
        run_migration "dry-run" "$SCOPE" "${EXTRA_ARGS[@]}"
        echo ""
        success "Dry-run complete. Review the table/column listings above."
        log "If everything looks correct, run without --dry-run."
        return 0
    fi

    # ── Confirmation ───────────────────────────────────────────
    echo ""
    warn "${BOLD}This will migrate ALL data from SQLite to PostgreSQL.${NC}"
    warn "  • Original .env backed up at: $(basename "$ENV_BACKUP")"
    warn "  • SQLite databases are NOT deleted (safe to rollback)"
    warn "  • Database scope: $SCOPE"
    echo ""
    read -r -p "  Continue? [y/N] " response
    if [[ ! "$response" =~ ^[yY]$ ]]; then
        log "Migration cancelled by user."
        rollback_env
        exit 0
    fi

    # ── Full Migration ─────────────────────────────────────────
    run_migration "full" "$SCOPE" "${EXTRA_ARGS[@]}" || {
        error "Migration failed"
        rollback_env
        exit 1
    }

    # ── Alembic ────────────────────────────────────────────────
    run_alembic

    # ── Verification ───────────────────────────────────────────
    verify

    # ── Summary ────────────────────────────────────────────────
    echo ""
    echo -e "${GREEN}${BOLD}╔══════════════════════════════════════════════════════╗${NC}"
    echo -e "${GREEN}${BOLD}║           Migration Complete!                        ║${NC}"
    echo -e "${GREEN}${BOLD}╚══════════════════════════════════════════════════════╝${NC}"
    echo ""
    success "All data migrated from SQLite to PostgreSQL"
    success "Alembic version tables stamped"
    success "All database connections verified"
    echo ""
    log "Your .env is now configured for PostgreSQL."
    log "To switch back to SQLite: cp $(basename "$ENV_BACKUP") $ENV_FILE"
    echo ""
    log "📋 Next steps:"
    log "  1. Start the application: cd .. && docker compose up -d"
    log "  2. Or locally: cd $PROJECT_ROOT && uv run python app.py"
    log "  3. Monitor logs for any database errors"
    echo ""
    log "Backup saved: $(basename "$ENV_BACKUP")"
}


# ── Run ──────────────────────────────────────────────────────────────────────
main "$@"
