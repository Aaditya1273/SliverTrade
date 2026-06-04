# SilverTrade AI — Alert Notification Setup Guide

Configure AlertManager to send real-time notifications when your trading platform experiences downtime, errors, or resource exhaustion.

---

## Table of Contents

1. [How Alert Routing Works](#1-how-alert-routing-works)
2. [Slack Integration](#2-slack-integration)
3. [PagerDuty Integration](#3-pagerduty-integration)
4. [Generic Webhook Integration](#4-generic-webhook-integration)
5. [Testing Alerts](#5-testing-alerts)
6. [Customizing Alert Templates](#6-customizing-alert-templates)
7. [Troubleshooting](#7-troubleshooting)

---

## 1. How Alert Routing Works

Alerts flow through a **route tree** in AlertManager that determines which notification channel receives which alert:

```
Prometheus Alert Fires
        │
        ▼
   ┌────────────┐
   │  Route     │
   │  Tree      │
   └─────┬──────┘
         │
    ┌────┴──────────────┐
    │                   │
    ▼                   ▼
┌────────┐        ┌──────────┐
│Critical│        │ Warning  │
│severity│        │ severity │
└───┬────┘        └────┬─────┘
    │                   │
    ▼                   ▼
┌────────────────┐ ┌──────────────┐
│ Slack #alerts- │ │ Slack        │
│ critical       │ │ #alerts-     │
│ PagerDuty      │ │ warning      │
│ Webhook        │ │ Webhook      │
└────────────────┘ └──────────────┘
```

| Alert Severity | Slack Channel | PagerDuty | Webhook |
|----------------|---------------|-----------|---------|
| **Critical** | `#alerts-critical` | ✅ Yes | ✅ Yes |
| **Warning** | `#alerts-warning` | ❌ No | ✅ Yes |
| **Platform-specific** | — | — | ✅ Yes |

### Inhibition Rules

To reduce noise, critical alerts **silence** warning-level alerts for the same service:

- If `PlatformDown` is firing → warnings about `PlatformHighErrorRate` are suppressed
- If `PostgreSQLDown` is firing → warnings about platform services are suppressed
- This means: you'll get one critical alert, not 10 related alerts

---

## 2. Slack Integration

### Step 1: Create a Slack App Webhook

1. Go to [api.slack.com/apps](https://api.slack.com/apps)
2. Click **Create New App** → **From scratch**
3. Name it `SilverTrade Alerts` and select your workspace
4. Navigate to **Incoming Webhooks** → **Activate Incoming Webhooks** → **On**
5. Click **Add New Webhook to Workspace**
6. Select the channel (e.g., `#alerts-critical` — you can create different channels for critical vs warning)
7. Copy the **Webhook URL** (looks like `https://hooks.slack.com/services/T00/B00/xxxxx`)

### Step 2: Set the Environment Variable

```bash
export SLACK_WEBHOOK_URL="https://hooks.slack.com/services/T00/B00/xxxxx"
```

**Security Note:** This URL is a secret — it allows posting to your Slack channel. Never commit it to version control. Set it as an environment variable on your server or in your CI/CD pipeline.

### Step 3: Restart the AlertManager

```bash
docker compose -f docker-compose.prod.yml up -d alertmanager
```

### What Slack Messages Look Like

#### Critical Alert (🔴)

```
🔴 [CRITICAL] PlatformDown — platform

Severity: Critical 🚨
Environment: Production
Alerts Firing: 1

── Active Alerts ──
• PlatformDown (critical)
  Service: `platform`
  Platform API has been unreachable for >1 minute.
  ▶ Action: Check platform container: docker compose logs platform
  Value: N/A | Since: 14:30:00 UTC

Recommended Action:
1. Check service logs: `docker compose logs platform`
2. Verify container status: `docker compose ps`
3. Escalate to: #oncall-sre
```

#### Warning Alert (⚠️)

```
⚠️ [WARNING] PlatformHighLatency — platform

Severity: Warning ⚠️
Environment: Production
Alerts Firing: 1

── Active Alerts ──
• PlatformHighLatency (warning)
  Service: `platform`
  P95 latency is 2.5s over the last 5 minutes (threshold: 2s).
  Value: N/A | Since: 14:25:00 UTC
```

#### Resolved Alert (✅)

```
✅ [RESOLVED] PlatformDown — platform

All 1 alerts for `platform` have been resolved.

── Resolved Alerts ──
• ✅ PlatformDown — Resolved at 14:45:00 UTC
```

---

## 3. PagerDuty Integration

PagerDuty is recommended for **critical alerts only** — warnings go to Slack alone.

### Step 1: Create a PagerDuty Service

1. Log in to your [PagerDuty account](https://www.pagerduty.com)
2. Navigate to **Services** → **Service Directory** → **New Service**
3. Name it `SilverTrade AI`
4. Under **Integration Type**, search for and select **Prometheus** (uses Events API v2)
5. Click **Create Service**
6. Copy the **Integration Key** (starts with a 32-character hex string)

### Step 2: Set the Environment Variable

```bash
export PAGERDUTY_ROUTING_KEY="your-32-char-pagerduty-key"
```

### Step 3: Configure Escalation Policies

In PagerDuty, set up an escalation policy that:

1. **Immediately notifies** the on-call engineer (SMS + phone call)
2. **Escalates to team lead** if not acknowledged within 5 minutes
3. **Escalates to management** if not acknowledged within 15 minutes

### What PagerDuty Incidents Look Like

When a critical alert fires, PagerDuty receives:

- **Title:** `[CRITICAL] PlatformDown — platform`
- **Severity:** `critical`
- **Description:** Formatted alert summary with all firing and resolved alerts
- **Details:** Alert count, resolved count, and service group labels
- **Client:** `SilverTrade AI`
- **Client URL:** Your platform's URL

PagerDuty will then trigger the escalation policy you configured.

---

## 4. Generic Webhook Integration

Use this for custom automation — triggering webhooks in tools like Zapier, n8n, custom scripts, or status page updates.

### Step 1: Set the Environment Variable

```bash
export WEBHOOK_URL="https://your-automation.example.com/hooks/silvertrade-alerts"
```

### Webhook Payload Format

AlertManager sends a POST request with the following JSON payload:

```json
{
  "receiver": "critical",
  "status": "firing",
  "alerts": [
    {
      "status": "firing",
      "labels": {
        "alertname": "PlatformDown",
        "severity": "critical",
        "service": "platform",
        "job": "silvertrade-platform"
      },
      "annotations": {
        "summary": "SilverTrade Platform is down",
        "description": "Platform API has been unreachable for >1 minute.",
        "action": "Check platform container: docker compose logs platform"
      },
      "startsAt": "2025-06-03T14:30:00Z",
      "endsAt": "0001-01-01T00:00:00Z"
    }
  ],
  "groupLabels": {
    "alertname": "PlatformDown",
    "severity": "critical",
    "service": "platform"
  },
  "commonLabels": {
    "env": "production",
    "monitor": "silvertrade"
  },
  "externalURL": "https://trade.example.com/alertmanager"
}
```

---

## 5. Testing Alerts

### Test with a Real Alert (Recommended)

```bash
# Simulate a service going down (replace "platform" with any service)
docker compose -f docker-compose.prod.yml stop platform

# Wait 1 minute for the alert to fire
# Check Slack #alerts-critical for the notification

# Restart the service to trigger the resolved notification
docker compose -f docker-compose.prod.yml start platform
```

### Test with amtool (AlertManager CLI)

```bash
# Create a test alert
docker compose -f docker-compose.prod.yml exec alertmanager \
  amtool alert add \
    --alertmanager.url=http://127.0.0.1:9093 \
    --annotation summary="Test alert" \
    --annotation description="This is a test alert" \
    --label severity=critical \
    --label service=platform \
    --label alertname=TestAlert \
    60s  # duration in seconds

# Check active alerts
docker compose -f docker-compose.prod.yml exec alertmanager \
  amtool alert query --alertmanager.url=http://127.0.0.1:9093
```

### Test the Slack Webhook Directly

```bash
# Verify the webhook URL works
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"🟢 SilverTrade AI — Alert test successful!"}' \
  $SLACK_WEBHOOK_URL
```

---

## 6. Customizing Alert Templates

Alert notification templates are in `monitoring/alertmanager/templates/default.tmpl`.

### Template Structure

```
default.tmpl
├── silvertrade.emoji           — 🔴 / ✅ based on alert status
├── silvertrade.duration         — Human-readable duration since alert started
├── silvertrade.alert_list       — Bulleted list of all firing alerts
├── silvertrade.resolved_list    — Bulleted list of resolved alerts
├── silvertrade.slack.critical.title  — Slack title for critical alerts
├── silvertrade.slack.critical.text   — Slack body for critical alerts
├── silvertrade.slack.warning.title   — Slack title for warning alerts
├── silvertrade.slack.warning.text    — Slack body for warning alerts
├── silvertrade.slack.resolved.title  — Slack title for resolved alerts
├── silvertrade.slack.resolved.text   — Slack body for resolved alerts
└── silvertrade.pagerduty.description — PagerDuty incident description
```

### Example: Customizing the Slack Message

Edit `monitoring/alertmanager/templates/default.tmpl`:

```gotmpl
{{- define "silvertrade.slack.critical.title" -}}
🔴 [CRITICAL] {{ .GroupLabels.alertname }} — {{ .GroupLabels.service }}
{{- end }}
```

Available template variables:

| Variable | Description |
|----------|-------------|
| `.Status` | `firing` or `resolved` |
| `.Alerts.Firing` | List of currently firing alerts |
| `.Alerts.Resolved` | List of resolved alerts |
| `.GroupLabels` | Labels common to the alert group |
| `.CommonLabels` | Labels common to all alerts |
| `.ExternalURL` | AlertManager external URL |

After editing templates, restart AlertManager:

```bash
docker compose -f docker-compose.prod.yml restart alertmanager
```

---

## 7. Troubleshooting

### Slack notifications not sending

```bash
# 1. Check if SLACK_WEBHOOK_URL is set correctly
docker compose -f docker-compose.prod.yml exec alertmanager env | grep SLACK

# 2. Check AlertManager logs for errors
docker compose -f docker-compose.prod.yml logs alertmanager

# 3. Test the webhook directly
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test"}' \
  $SLACK_WEBHOOK_URL

# 4. Restart AlertManager
docker compose -f docker-compose.prod.yml restart alertmanager
```

### PagerDuty not creating incidents

```bash
# 1. Verify the routing key
docker compose -f docker-compose.prod.yml exec alertmanager env | grep PAGERDUTY

# 2. Check AlertManager logs for PagerDuty errors
docker compose -f docker-compose.prod.yml logs alertmanager 2>&1 | grep -i pagerduty

# 3. Verify the integration key in PagerDuty dashboard
#    Service → SilverTrade AI → Integrations → Prometheus
```

### Alerts not firing at all

```bash
# 1. Check if Prometheus is evaluating rules
curl http://localhost:9090/api/v1/rules | python3 -m json.tool

# 2. Force-evaluate rules
curl -X POST http://localhost:9090/-/reload

# 3. Check AlertManager is reachable from Prometheus
docker compose -f docker-compose.prod.yml exec prometheus \
  wget -qO- http://alertmanager:9093/-/ready
```

### Alert fatigue (too many alerts)

Edit `monitoring/prometheus/alerts/service-down.yml` to:

- **Increase** the `for:` duration (e.g., change `1m` to `5m` for less sensitive downtime alerts)
- **Increase** the threshold (e.g., change `> 0.05` to `> 0.10` for error rate)
- **Remove** low-value alerts entirely

Then reload Prometheus:

```bash
curl -X POST http://localhost:9090/-/reload
```
