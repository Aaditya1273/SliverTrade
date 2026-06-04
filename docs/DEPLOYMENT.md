# SilverTrade AI — Deployment Guide

## Table of Contents
1. [Quick Start (5 minutes)](#quick-start)
2. [Development Deployment](#development-deployment)
3. [Production Deployment](#production-deployment)
4. [Cloud Deployment (Railway/Render)](#cloud-deployment)
5. [Docker Reference](#docker-reference)
6. [SSL Setup](#ssl-setup)
7. [Updating](#updating)
8. [Troubleshooting](#troubleshooting)

---

## Quick Start

```bash
# 1. Clone the repository
git clone https://github.com/marketcalls/silvertrade.git
cd silvertrade

# 2. Configure environment
cp Platfrom/.env.production Platfrom/.env
# Edit Platfrom/.env with your values (API keys, secrets, etc.)

# 3. Start with Docker Compose
docker compose -f docker-compose.prod.yml up -d

# 4. Verify all services are healthy
bash deploy/health-check.sh --verbose

# 5. Access the dashboard
open http://localhost:3000
```

**Next steps:**
- Set up SSL: [SSL Setup](#ssl-setup)
- Configure alerts: [docs/ALERTS.md](ALERTS.md)
- View monitoring: [docs/MONITORING.md](MONITORING.md)

---

## Development Deployment

### Prerequisites

- Python 3.12+
- Node.js 20+
- npm or pnpm

### Backend (Platform)

```bash
# Navigate to platform directory
cd Platfrom

# Create virtual environment
python3 -m venv .venv
source .venv/bin/activate  # Linux/Mac
# .venv\Scripts\activate    # Windows

# Install dependencies
pip install uv
uv sync

# Configure environment
cp .env.production .env
# Edit .env for development (set FLASK_DEBUG=True)

# Start the platform
python app.py
# Server runs at http://127.0.0.1:5000
```

### Data Fetch Service

```bash
cd data_fetch
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
cp .env.sample .env
python app.py
# Server runs at http://127.0.0.1:5005
```

### Strategy Engine

```bash
cd Trade_Strategies
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
python strategies_app.py
# Server runs at http://127.0.0.1:5007
```

### Frontend (UI)

```bash
cd ui
npm install
npm run dev
# Server runs at http://127.0.0.1:3000
```

### Using PM2 (Process Manager)

```bash
# From project root
npm install pm2
bash start_all.sh
# Or directly:
npx pm2 start ecosystem.config.js
npx pm2 logs  # View logs from all services
```

---

## Production Deployment

### Prerequisites

- Docker 24+ and Docker Compose plugin
- Domain name pointed to your server's IP
- Ports 80 and 443 open in firewall

### Step 1: Server Preparation

```bash
# Update system
sudo apt update && sudo apt upgrade -y

# Install Docker
curl -fsSL https://get.docker.com | sh
sudo usermod -aG docker $USER
newgrp docker

# Install Docker Compose
sudo apt install docker-compose-plugin

# Clone repository
git clone https://github.com/marketcalls/silvertrade.git
cd silvertrade
```

### Step 2: Configure Environment

```bash
# Copy production env template
cp Platfrom/.env.production Platfrom/.env

# Edit with your values
nano Platfrom/.env
```

**Required values in `.env`:**
| Variable | Description |
|----------|-------------|
| `HOST_SERVER` | Your domain (e.g., `https://trade.example.com`) |
| `REDIRECT_URL` | Broker OAuth callback |
| `APP_KEY` | Generate: `python3 -c "import secrets; print(secrets.token_hex(32))"` |
| `API_KEY_PEPPER` | Generate another one |
| `BROKER_API_KEY` | Your broker API key |
| `BROKER_API_SECRET` | Your broker API secret |

### Step 3: SSL Certificates

```bash
# Option A: Auto with Let's Encrypt
export DOMAIN=trade.example.com
export EMAIL=admin@example.com
bash deploy/init-letsencrypt.sh

# Option B: Use existing certificates
# Place your fullchain.pem and privkey.pem in:
#   certbot/conf/live/trade.example.com/
```

### Step 4: Deploy

```bash
# Full production deploy
bash deploy/deploy.sh

# Or step by step:
docker compose -f docker-compose.prod.yml up -d

# Monitor startup
docker compose -f docker-compose.prod.yml logs -f
```

### Step 5: Verify

```bash
# Run health check
bash deploy/health-check.sh --verbose

# Check individual services
curl https://trade.example.com/api/v1/health
curl https://trade.example.com/strategies/api/v1/health
curl https://trade.example.com/data-fetch/api/health

# Access Grafana (credentials: admin / silvertrade)
open https://trade.example.com/grafana
```

---

## Cloud Deployment (Railway / Render)

SilverTrade AI can be deployed on Railway, Render, or similar platforms.

### Environment Variables (Required)

Set these in your cloud dashboard:

```bash
# Core
HOST_SERVER=https://your-app.up.railway.app
REDIRECT_URL=https://your-app.up.railway.app/zerodha/callback

# Secrets (generate with python3 -c "import secrets; print(secrets.token_hex(32))")
APP_KEY=<generate-me>
API_KEY_PEPPER=<generate-me>

# Broker
BROKER_API_KEY=your_key
BROKER_API_SECRET=your_secret

# Database (use managed PostgreSQL)
DATABASE_URL=postgresql://user:pass@host:5432/silvertrade
```

### Platform-Specific Notes

**Railway:**
- The `start.sh` script auto-detects Railway via `$HOST_SERVER` env var
- Railway's `$PORT` is automatically used by the gunicorn config
- No `.env` file needed — all config from environment variables
- WebSocket support requires `WEBSOCKET_HOST=0.0.0.0`

**Render:**
- Use a Web Service for the platform
- Set `APP_MODE=standalone` for Docker deployment
- Health check path: `/api/v1/health`
- WebSocket support requires sticky sessions

---

## Docker Reference

### Production Compose (`docker-compose.prod.yml`)

| Service | Image/Context | Internal Port | Description |
|---------|---------------|---------------|-------------|
| `postgres` | postgres:16-alpine | 5432 | Production database |
| `redis` | redis:7-alpine | 6379 | Cache & rate limiting |
| `platform` | ./Platfrom/Dockerfile | 5000 | Main API |
| `data_fetch` | ./data_fetch/Dockerfile | 5005 | Market data |
| `trade_strategies` | ./Trade_Strategies/Dockerfile | 5007 | AI engine |
| `ui` | ./ui/Dockerfile | 3000 | Next.js dashboard |
| `nginx` | nginx:1.25-alpine | 80/443 | Reverse proxy |
| `certbot` | certbot/certbot | - | SSL management |
| `postgres-exporter` | prometheuscommunity/postgres-exporter | 9187 | PG metrics |
| `redis-exporter` | oliver006/redis_exporter | 9121 | Redis metrics |
| `cadvisor` | gcr.io/cadvisor/cadvisor | 8080 | Container metrics |
| `node-exporter` | prom/node-exporter | 9100 | Host metrics |
| `prometheus` | prom/prometheus | 9090 | Metrics collection |
| `alertmanager` | ./monitoring/alertmanager/Dockerfile | 9093 | Alert routing |
| `grafana` | grafana/grafana | 3001 | Dashboards |

### Common Commands

```bash
# Start all services
docker compose -f docker-compose.prod.yml up -d

# View logs for a specific service
docker compose -f docker-compose.prod.yml logs -f platform

# Rebuild a single service
docker compose -f docker-compose.prod.yml build platform

# Restart a service
docker compose -f docker-compose.prod.yml restart nginx

# Check service status
docker compose -f docker-compose.prod.yml ps

# Stop all services
docker compose -f docker-compose.prod.yml down

# Stop and remove volumes (destroys data)
docker compose -f docker-compose.prod.yml down -v

# Scale a service (if applicable)
docker compose -f docker-compose.prod.yml up -d --scale platform=2
```

---

## SSL Setup

### Automatic (Let's Encrypt)

```bash
export DOMAIN=trade.example.com
export EMAIL=admin@example.com
bash deploy/init-letsencrypt.sh
```

This script:
1. Starts nginx in HTTP-only mode
2. Runs Certbot with webroot validation
3. Obtains SSL certificates
4. Restarts the full stack with HTTPS
5. Certificates auto-renew every 12 hours

### Manual (Existing Certificates)

```bash
# Place certificates
mkdir -p certbot/conf/live/trade.example.com
cp /path/to/fullchain.pem certbot/conf/live/trade.example.com/
cp /path/to/privkey.pem certbot/conf/live/trade.example.com/

# Set permissions
chmod 600 certbot/conf/live/trade.example.com/privkey.pem

# Start stack
docker compose -f docker-compose.prod.yml up -d
```

---

## Updating

### Quick Update (code changes only)

```bash
git pull
bash deploy/deploy.sh --quick
```

### Full Update (with rebuild)

```bash
git pull
bash deploy/deploy.sh
```

### Database Migrations

Migrations run automatically on startup via `start.sh`. To run manually:

```bash
docker compose -f docker-compose.prod.yml exec platform python upgrade/migrate_all.py
```

---

## Troubleshooting

### Services won't start

```bash
# Check logs
docker compose -f docker-compose.prod.yml logs

# Check if ports are in use
sudo lsof -i :5000 -i :5432 -i :6379

# Verify .env configuration
docker compose -f docker-compose.prod.yml config
```

### Database connection errors

```bash
# Verify PostgreSQL is healthy
docker compose -f docker-compose.prod.yml ps postgres

# Check PostgreSQL logs
docker compose -f docker-compose.prod.yml logs postgres

# Verify connection string
docker compose -f docker-compose.prod.yml exec postgres pg_isready -U silvertrade
```

### SSL certificate issues

```bash
# Check certificate expiry
docker compose -f docker-compose.prod.yml run --rm certbot certificates

# Force renewal
docker compose -f docker-compose.prod.yml run --rm certbot renew --force-renewal

# Reload nginx
docker compose -f docker-compose.prod.yml exec nginx nginx -s reload
```

### WebSocket connection fails

```bash
# Verify WebSocket proxy is running
docker compose -f docker-compose.prod.yml logs platform | grep WebSocket

# Check WebSocket port
docker compose -f docker-compose.prod.yml exec platform curl -I http://127.0.0.1:8765

# Nginx WebSocket timeout (default: 86400s)
# Check /ws location block in nginx/conf.d/default.conf
```

### High memory usage

```bash
# Check per-container memory
docker stats

# Adjust thread limits in .env
OPENBLAS_NUM_THREADS=1
OMP_NUM_THREADS=1
NUMBA_NUM_THREADS=1

# Restart after changes
docker compose -f docker-compose.prod.yml down
docker compose -f docker-compose.prod.yml up -d
```
