# SilverTrade AI — Monitoring Guide

This guide covers the complete monitoring stack: Prometheus metrics collection, Grafana dashboards, AlertManager alerting, and how to interpret the dashboards.

---

## Table of Contents

1. [Architecture Overview](#1-architecture-overview)
2. [Accessing Grafana](#2-accessing-grafana)
3. [Pre-Built Dashboard: Platform Overview](#3-pre-built-dashboard-platform-overview)
4. [Prometheus Metrics](#4-prometheus-metrics)
5. [AlertManager](#5-alertmanager)
6. [Custom Queries](#6-custom-queries)
7. [Troubleshooting the Monitoring Stack](#7-troubleshooting-the-monitoring-stack)

---

## 1. Architecture Overview

```
┌──────────────────────────────────────────────────────────────────┐
│                    Monitoring Stack                               │
├────────────┬────────────┬────────────┬───────────┬───────────────┤
│  Platform  │  Data      │  Strategy  │  Nginx    │  UI           │
│  Flasks    │  Fetch     │  Engine    │  stub_    │  (Next.js)    │
│  /metrics  │  /metrics  │  /metrics  │  status   │  /api/metrics │
└────────────┴────────────┴────────────┴───────────┴───────────────┘
       │            │            │           │              │
       └────────────┴────────────┴───────────┴──────────────┘
                              │
                     ┌────────▼────────┐
                     │   Prometheus    │
                     │   :9090         │
                     │   30d retention │
                     └────────┬────────┘
                              │
                  ┌───────────┼───────────┐
                  │           │           │
           ┌──────▼────┐ ┌───▼───┐ ┌─────▼─────┐
           │  Grafana  │ │AlertM │ │ Slack /    │
           │  :3001    │ │:9093  │ │ PagerDuty  │
           │  proxied  │ │       │ │            │
           │  /grafana │ │       │ │            │
           └───────────┘ └───────┘ └────────────┘
```

**Infrastructure exporters also feed Prometheus:**

| Exporter | Source | Metrics |
|----------|--------|---------|
| `postgres-exporter:9187` | PostgreSQL | Queries, connections, cache hit rate |
| `redis-exporter:9121` | Redis | Memory, hit rate, keyspace stats |
| `cadvisor:8080` | Docker containers | CPU, memory, network, disk per container |
| `node-exporter:9100` | Host machine | CPU, load, disk, network interfaces |

---

## 2. Accessing Grafana

### Via Nginx (production)

```
https://trade.example.com/grafana
```

### Direct (development)

```
http://localhost:3001
```

### Default Credentials

| Field | Default Value |
|-------|---------------|
| Username | `admin` |
| Password | `silvertrade` |

**Change immediately in production** by setting these environment variables:

```bash
export GRAFANA_USER=myadmin
export GRAFANA_PASSWORD=<strong-password>
```

### Data Source

The Prometheus data source is **auto-provisioned** — you don't need to configure anything. On first login, navigate to **Configuration → Data Sources** and you'll see `SilverTrade Prometheus` already configured pointing to `http://prometheus:9090`.

---

## 3. Pre-Built Dashboard: Platform Overview

A 16-panel dashboard is auto-loaded at login. Here's a panel-by-panel walkthrough:

### Row 1: Health & Traffic (Panels 1–5)

| # | Panel | Type | What to Watch |
|---|-------|------|---------------|
| 1 | **Service Health** | Stat | Shows count of healthy SilverTrade services. Should be **8+** when all services are up. Turns red if <6. |
| 2 | **API Request Rate** | Graph | Request rate broken down by HTTP status class (2xx, 4xx, 5xx). Normal: mostly 2xx with occasional 4xx. Sustained 5xx >5% is an issue. |
| 3 | **P95 Latency** | Graph | Request latency percentiles (P50, P95, P99). Normal P95: **<500ms**. Warning threshold: **>2s**. |
| 4 | **Error Rate** | Graph | Percentage of 5xx responses. Normal: **<1%**. Warning: **>5%** triggers AlertManager alert. |
| 5 | **Active WebSocket Connections** | Stat | Number of live WebSocket connections. Should reflect active users/trading terminals. |

### Row 2: Container Resources (Panels 6–8)

| # | Panel | Type | What to Watch |
|---|-------|------|---------------|
| 6 | **Container CPU Usage** | Graph | CPU per container. Spikes during strategy computation and data fetching. Sustained >80% requires investigation. |
| 7 | **Container Memory Usage** | Graph | Memory per container in MB. Watch for continuous upward trends (memory leak). |
| 8 | **Network I/O** | Graph | Network throughput per container. High values on `platform` indicate active trading. |

### Row 3: Infrastructure (Panels 9–13)

| # | Panel | Type | What to Watch |
|---|-------|------|---------------|
| 9 | **PostgreSQL Connections** | Graph | Active vs max database connections. Watch for connection pool exhaustion. |
| 10 | **Redis Memory Usage** | Graph | Used vs max Redis memory. Should stay well below 512MB limit. |
| 11 | **Redis Hit Rate** | Graph | Cache effectiveness. **>90%** is healthy. Below 80% indicates cache thrashing. |
| 12 | **Host Disk Usage** | Gauge | Root filesystem free space. **Alert triggers at <10% free.** |
| 13 | **System Load** | Graph | Load averages (1m, 5m, 15m). Sustained load > CPU cores indicates saturation. |

### Row 4: Operations (Panels 14–16)

| # | Panel | Type | What to Watch |
|---|-------|------|---------------|
| 14 | **Active Alerts** | Alert list | Currently firing Prometheus alerts. Shows severity and alert name. |
| 15 | **Service Uptime** | Table | Uptime of each SilverTrade service since last restart. Useful after deployments. |
| 16 | **Request Rate by Endpoint (Top 10)** | Table | Most requested API endpoints. Helps identify usage patterns and potential abuse. |

### Dashboard Variables

The dashboard has a **Data Source** dropdown at the top. It defaults to the provisioned Prometheus datasource.

---

## 4. Prometheus Metrics

### Available Metric Endpoints

| Service | Endpoint | Example Query |
|---------|----------|---------------|
| Platform API | `https://trade.example.com/metrics` | `flask_http_request_total` |
| Data Fetch | `http://data_fetch:5005/metrics` | `flask_http_request_duration_seconds` |
| Strategy Engine | `http://trade_strategies:5007/metrics` | `python_info` |
| Postgres | `http://postgres-exporter:9187/metrics` | `pg_stat_activity_count` |
| Redis | `http://redis-exporter:9121/metrics` | `redis_memory_used_bytes` |
| Nginx | `http://nginx:80/nginx-status` | `nginx_connections_active` |
| Containers | `http://cadvisor:8080/metrics` | `container_cpu_usage_seconds_total` |
| Host | `http://node-exporter:9100/metrics` | `node_load1` |

### Useful PromQL Queries

#### Service Health

```promql
# Are all services up?
count(up{job=~"silvertrade-.*"} == 1)

# Which services are down?
up{job=~"silvertrade-.*"} == 0
```

#### API Performance

```promql
# Request rate by endpoint (last 5m)
sum(rate(flask_http_request_duration_seconds_count[5m])) by (path)

# P95 latency by endpoint
histogram_quantile(0.95, sum(rate(flask_http_request_duration_seconds_bucket[5m])) by (le, path))

# Error rate percentage
(sum(rate(flask_http_request_duration_seconds_count{status=~"5.."}[5m])) / sum(rate(flask_http_request_duration_seconds_count[5m]))) * 100
```

#### Infrastructure

```promql
# PostgreSQL connection utilization
pg_stat_activity_count / pg_stat_activity_max * 100

# Redis cache hit ratio
rate(redis_keyspace_hits_total[5m]) / (rate(redis_keyspace_hits_total[5m]) + rate(redis_keyspace_misses_total[5m])) * 100

# Container memory trend (detect leaks)
container_memory_usage_bytes{name=~"silvertrade-.*"} / 1048576
```

---

## 5. AlertManager

### Access

AlertManager is available at:

```
https://trade.example.com/alertmanager
```

### Pre-Configured Alerts

The monitoring stack ships with 15 alert rules across 4 categories:

#### Service Down (Critical)

| Alert | Condition | Response |
|-------|-----------|----------|
| `PlatformDown` | `up{job="platform"} == 0` for 1m | Check platform container |
| `DataFetchDown` | `up{job="data-fetch"} == 0` for 1m | Check data_fetch container |
| `StrategyEngineDown` | `up{job="strategy-engine"} == 0` for 1m | Check trade_strategies container |
| `UIDown` | `up{job="ui"} == 0` for 1m | Check ui container |
| `NginxDown` | `up{job="nginx"} == 0` for 1m | Check nginx container (all traffic affected) |
| `PostgreSQLDown` | `up{job="postgres"} == 0` for 1m | Check postgres container |
| `RedisDown` | `up{job="redis"} == 0` for 1m | Check redis container |

#### High Error Rates (Warning)

| Alert | Condition | Response |
|-------|-----------|----------|
| `PlatformHighErrorRate` | 5xx rate >5% for 5m | Check recent code changes or broker API |
| `PlatformHighLatency` | P95 latency >2s for 5m | Scale up or optimize slow endpoints |

#### Resource Exhaustion (Warning)

| Alert | Condition | Response |
|-------|-----------|----------|
| `ContainerHighCPU` | CPU >80% for 10m | Scale up or investigate CPU-bound process |
| `ContainerHighMemory` | Memory >85% for 10m | Check for memory leak or increase limits |
| `HostDiskSpace` | Disk <10% free for 5m | Clean up or expand storage |
| `HostHighLoad` | Load >80% of CPU cores for 10m | Scale up or migrate to larger instance |

### Alert Silencing

To silence an alert temporarily:

```
AlertManager UI → Silences → New Silence
```

Set the duration and label matcher (e.g., `alertname = "HostDiskSpace"`) — useful during planned maintenance.

---

## 6. Custom Queries

### Creating Ad-Hoc Panels

1. Open Grafana → **+** → **Dashboard**
2. Click **Add panel** → **Add a new panel**
3. Switch to **Code** mode (not Builder)
4. Enter any PromQL query from [Section 4](#useful-promql-queries)
5. Adjust time range in the top right corner

### Example: Multi-Service Latency Comparison

```promql
# Compare P95 latency across all services
histogram_quantile(0.95, sum(rate(flask_http_request_duration_seconds_bucket[5m])) by (le, job))
```

### Example: Detect Anomalous Traffic Spikes

```promql
# Sudden increase in request rate (Z-score style)
deriv(rate(flask_http_request_duration_seconds_count[15m])[30m:1m]) > 0.1
```

---

## 7. Troubleshooting the Monitoring Stack

### "No data" in Grafana dashboards

```bash
# 1. Verify Prometheus is collecting data
curl http://localhost:9090/api/v1/targets | python3 -m json.tool

# 2. Check if the Flask /metrics endpoint is accessible
curl http://localhost:5000/metrics | head -20

# 3. Verify Grafana datasource
curl http://localhost:3001/api/datasources
```

### "Service Down" alert immediately after deploy

This is normal during startup. The alert has a `for: 1m` clause — it only fires if the service is down for a full minute. Allow 60–90s after `docker compose up -d` for all healthchecks to pass.

### Prometheus targets show "DOWN"

```bash
# Check if the target service is reachable from Prometheus container
docker compose -f docker-compose.prod.yml exec prometheus wget -qO- http://platform:5000/metrics
```

### AlertManager not sending Slack notifications

```bash
# 1. Verify SLACK_WEBHOOK_URL is set
docker compose -f docker-compose.prod.yml exec alertmanager env | grep SLACK

# 2. Check AlertManager logs
docker compose -f docker-compose.prod.yml logs alertmanager

# 3. Verify the webhook URL is valid
curl -X POST -H 'Content-type: application/json' \
  --data '{"text":"Test from SilverTrade"}' \
  $SLACK_WEBHOOK_URL
```

### Viewing raw Prometheus rules

```bash
# Check which rules are loaded
curl http://localhost:9090/api/v1/rules | python3 -m json.tool
```
