# SilverTrade AI — Quickstart Guide

Get SilverTrade AI running in 5 minutes — from zero to a live dashboard.

---

## Prerequisites

- [Docker](https://docs.docker.com/get-docker/) 24+ (with Compose plugin)
- A domain name pointed to your server (for production)

---

## 🚀 1-Minute: Clone & Configure

```bash
# Clone the repository
git clone https://github.com/marketcalls/silvertrade.git
cd silvertrade

# Copy the production environment template
cp Platfrom/.env.production Platfrom/.env
```

Generate required secrets:

```bash
python3 -c "
import secrets
key1 = secrets.token_hex(32)
key2 = secrets.token_hex(32)
print(f'APP_KEY={key1}')
print(f'API_KEY_PEPPER={key2}')
"
```

Edit `Platfrom/.env` and set at minimum:

```bash
HOST_SERVER=https://trade.yourdomain.com
APP_KEY=<paste-key1>
API_KEY_PEPPER=<paste-key2>
BROKER_API_KEY=your_broker_key
BROKER_API_SECRET=your_broker_secret
REDIRECT_URL=https://trade.yourdomain.com/zerodha/callback
```

---

## 🚀 2-Minute: Start the Stack

```bash
# Start all services
docker compose -f docker-compose.prod.yml up -d

# Check startup progress
docker compose -f docker-compose.prod.yml ps
```

Expected output (after 30-60s for healthchecks):

```
NAME                         STATUS
silvertrade-postgres         Up About a minute (healthy)
silvertrade-redis            Up About a minute (healthy)
silvertrade-platform         Up About a minute (healthy)
silvertrade-data-fetch       Up About a minute (healthy)
silvertrade-strategies       Up About a minute (healthy)
silvertrade-ui               Up About a minute (healthy)
silvertrade-nginx            Up About a minute (healthy)
silvertrade-certbot          Up About a minute
silvertrade-prometheus       Up About a minute (healthy)
silvertrade-alertmanager     Up About a minute (healthy)
silvertrade-grafana          Up About a minute (healthy)
```

---

## 🚀 3-Minute: Verify Health

```bash
# Run the health check script
bash deploy/health-check.sh --verbose
```

Expected result:

```
✅ Platform API      — http://localhost:5000/api/v1/health       → 200 OK
✅ Data Fetch        — http://localhost:5005/api/health          → 200 OK
✅ Strategy Engine   — http://localhost:5007/api/v1/health       → 200 OK
✅ UI Dashboard      — http://localhost:3000                     → 200 OK
All 4 services are healthy.
```

---

## 🚀 4-Minute: Access the Dashboard

| Service | URL | Notes |
|---------|-----|-------|
| **UI Dashboard** | `http://localhost:3000` | Main trading interface |
| **Platform API** | `http://localhost:5000/api/v1` | REST API root |
| **Data Fetch** | `http://localhost:5005/api/data` | Market data |
| **Strategy Engine** | `http://localhost:5007/api/v1/decision` | AI trading signals |
| **Grafana** | `http://localhost:3001` | Monitoring (admin/silvertrade) |
| **Prometheus** | `http://localhost:9090` | Metrics |
| **AlertManager** | `http://localhost:9093` | Alerts |

> **Production Note:** When SSL is configured, all services are accessible through `https://trade.yourdomain.com/` with nginx routing.

---

## 🚀 5-Minute: Set Up SSL (Production Only)

```bash
export DOMAIN=trade.yourdomain.com
export EMAIL=admin@yourdomain.com
bash deploy/init-letsencrypt.sh
```

This obtains Let's Encrypt certificates and enables HTTPS.

---

## Next Steps

| Guide | What You'll Learn |
|-------|-------------------|
| [Deployment Guide](DEPLOYMENT.md) | Full production deployment, cloud deployment, Docker reference |
| [Environment Variables](ENVIRONMENT.md) | Complete env vars reference (200+ variables) |
| [Monitoring Guide](MONITORING.md) | Grafana dashboards, Prometheus queries, interpreting metrics |
| [Alert Setup Guide](ALERTS.md) | Slack, PagerDuty, webhook integration |
| [Architecture Overview](ARCHITECTURE.md) | System design, service topology, data flow |

---

## Useful Commands

```bash
# View logs for a specific service
docker compose -f docker-compose.prod.yml logs -f platform

# Rebuild a single service after code changes
docker compose -f docker-compose.prod.yml up -d --build platform

# Stop everything
docker compose -f docker-compose.prod.yml down

# Stop and delete all data (volumes)
docker compose -f docker-compose.prod.yml down -v
```

---

## Troubleshooting

**Services not starting?**
```bash
docker compose -f docker-compose.prod.yml logs
```

**Can't connect to broker?**
```bash
docker compose -f docker-compose.prod.yml logs platform | grep -i broker
```

**Need help?**
- Check all docs in the `docs/` directory
- Open an issue on GitHub
