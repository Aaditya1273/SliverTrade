#!/bin/bash
# =============================================================================
# SilverTrade AI — Automated Backups (Phase 9)
# =============================================================================
# Daily backup: PostgreSQL dumps + encryption + S3 upload
# =============================================================================

set -euo pipefail

DATE=$(date +%Y%m%d_%H%M%S)
BACKUP_DIR="/backups/$DATE"
mkdir -p "$BACKUP_DIR"

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
NC='\033[0m'

log() { echo -e "${GREEN}[$(date +'%Y-%m-%d %H:%M:%S')]${NC} $1"; }
error() { echo -e "${RED}ERROR:${NC} $1"; }

log "Starting backup: $DATE"

# Check required environment variables
if [ -z "${DATABASE_URL:-}" ]; then
    error "DATABASE_URL not set"
    exit 1
fi

if [ -z "${BACKUP_PASSPHRASE:-}" ]; then
    error "BACKUP_PASSPHRASE not set"
    exit 1
fi

if [ -z "${BACKUP_BUCKET:-}" ]; then
    error "BACKUP_BUCKET not set"
    exit 1
fi

# Dump all databases
log "Dumping databases..."
if command -v pg_dump &> /dev/null; then
    pg_dump "$DATABASE_URL" > "$BACKUP_DIR/main.sql"
    
    if [ -n "${LOGS_DATABASE_URL:-}" ]; then
        pg_dump "$LOGS_DATABASE_URL" > "$BACKUP_DIR/logs.sql"
    fi
    
    if [ -n "${SANDBOX_DATABASE_URL:-}" ]; then
        pg_dump "$SANDBOX_DATABASE_URL" > "$BACKUP_DIR/sandbox.sql"
    fi
    
    log "✅ Database dumps complete"
else
    error "pg_dump not found. Install PostgreSQL client tools."
    exit 1
fi

# Encrypt with GPG
log "Encrypting backups..."
if command -v gpg &> /dev/null; then
    for f in "$BACKUP_DIR"/*.sql; do
        gpg --symmetric --cipher-algo AES256 --batch \
            --passphrase "$BACKUP_PASSPHRASE" "$f"
        rm "$f"
    done
    log "✅ Encryption complete"
else
    error "gpg not found. Install GPG."
    exit 1
fi

# Upload to S3
log "Uploading to S3..."
if command -v aws &> /dev/null; then
    aws s3 sync "$BACKUP_DIR" "s3://$BACKUP_BUCKET/silvertrade/$DATE/"
    log "✅ S3 upload complete"
else
    error "AWS CLI not found. Install AWS CLI."
    exit 1
fi

# Delete local backups older than 7 days
log "Cleaning old local backups..."
find /backups -type d -mtime +7 -exec rm -rf {} +
log "✅ Cleanup complete"

log "Backup complete: $DATE"

# Send notification (optional)
if [ -n "${SLACK_WEBHOOK_URL:-}" ]; then
    curl -X POST "$SLACK_WEBHOOK_URL" \
        -H 'Content-Type: application/json' \
        -d "{\"text\": \"✅ SilverTrade AI backup completed: $DATE\"}"
fi
