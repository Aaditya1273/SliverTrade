#!/bin/sh
# =============================================================================
# SilverTrade AI — AlertManager Entrypoint
# =============================================================================
# Reads environment variables for Slack/PagerDuty webhook URLs and injects
# them into the AlertManager config before starting. This keeps secrets out
# of version control.
#
# Usage:
#   SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
#   PAGERDUTY_ROUTING_KEY=your-pagerduty-integration-key
#   WEBHOOK_URL=https://your-webhook-receiver.example.com/hooks
#
# If a variable is empty/unset, that receiver is configured with a no-op
# URL (localhost loopback) so AlertManager doesn't error on startup.
# =============================================================================

set -euo pipefail

CONFIG_FILE="/etc/alertmanager/config.yml"
TEMPLATES_DIR="/etc/alertmanager/templates"
SLACK_URL="${SLACK_WEBHOOK_URL:-}"
PD_KEY="${PAGERDUTY_ROUTING_KEY:-}"
WEBHOOK_URL="${WEBHOOK_URL:-}"

# ── Validate config file exists ─────────────────────────────────────────────
if [ ! -f "$CONFIG_FILE" ]; then
    echo "[AlertManager] FATAL: Config file not found at $CONFIG_FILE"
    exit 1
fi

echo "[AlertManager] Initializing SilverTrade AI alert routing..."
echo "[AlertManager]   Config: $CONFIG_FILE"
echo "[AlertManager]   Templates: $TEMPLATES_DIR"

# ── Create a temporary config with resolved webhook URLs ────────────────────
TMP_CONFIG="/tmp/alertmanager.yml"

# Read the existing config and replace placeholder URLs with actual env vars
cp "$CONFIG_FILE" "$TMP_CONFIG"

# Slack — replaces full pattern {{ .ExternalURL }}/slack
if [ -n "$SLACK_URL" ]; then
    sed -i "s|{{ .ExternalURL }}/slack|$SLACK_URL|g" "$TMP_CONFIG"
    echo "[AlertManager] ✓ Slack webhook configured"
else
    sed -i "s|{{ .ExternalURL }}/slack|http://localhost:9093/|g" "$TMP_CONFIG"
    echo "[AlertManager] - Slack webhook not set (alerts logged to console only)"
fi

# Generic Webhook — replaces {{ .ExternalURL }}/webhook (must run BEFORE PagerDuty
# to avoid the bare {{ .ExternalURL }} sed consuming the /webhook suffix)
if [ -n "$WEBHOOK_URL" ]; then
    sed -i "s|{{ .ExternalURL }}/webhook|$WEBHOOK_URL|g" "$TMP_CONFIG"
    echo "[AlertManager] ✓ Custom webhook configured"
else
    sed -i "s|{{ .ExternalURL }}/webhook|http://localhost:9093/|g" "$TMP_CONFIG"
    echo "[AlertManager] - Custom webhook not set"
fi

# PagerDuty — replaces remaining bare {{ .ExternalURL }} (runs LAST so
# it doesn't consume the /webhook or /slack suffixes of other placeholders)
if [ -n "$PD_KEY" ]; then
    sed -i "s|{{ .ExternalURL }}|$PD_KEY|g" "$TMP_CONFIG"
    echo "[AlertManager] ✓ PagerDuty integration configured"
else
    sed -i "s|routing_key: '{{ .ExternalURL }}'|routing_key: 'noop'|g" "$TMP_CONFIG"
    echo "[AlertManager] - PagerDuty not configured"
fi

# ── Validate the resulting config ───────────────────────────────────────────
if amtool check-config "$TMP_CONFIG" > /dev/null 2>&1; then
    echo "[AlertManager] ✓ Config validation passed"
else
    echo "[AlertManager] ⚠ Config validation warning (continuing)..."
fi

# ── Start AlertManager ──────────────────────────────────────────────────────
echo "[AlertManager] Starting..."
exec /bin/alertmanager \
    --config.file="$TMP_CONFIG" \
    --storage.path=/alertmanager \
    --web.external-url="${ALERTMANAGER_URL:-http://localhost:9093}" \
    --cluster.listen-address="" \
    "$@"
