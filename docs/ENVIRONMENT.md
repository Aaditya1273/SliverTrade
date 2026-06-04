# SilverTrade AI — Environment Variables Reference

This document describes every environment variable used across all SilverTrade services (Platform, Data Fetch, Strategy Engine, UI, and Monitoring).

**Source of truth:** `Platfrom/.env.production` is the master template. Copy it to `Platfrom/.env` and edit for your deployment.

---

## Table of Contents

1. [Core Platform Variables](#1-core-platform-variables)
2. [Broker Configuration](#2-broker-configuration)
3. [Database Configuration](#3-database-configuration)
4. [Redis Configuration](#4-redis-configuration)
5. [WebSocket Configuration](#5-websocket-configuration)
6. [Security & Authentication](#6-security--authentication)
7. [Rate Limiting](#7-rate-limiting)
8. [CORS & CSP](#8-cors--csp)
9. [Logging](#9-logging)
10. [Monitoring & Alerting](#10-monitoring--alerting)
11. [Service Discovery](#11-service-discovery)
12. [Data Fetch Service](#12-data-fetch-service)
13. [Strategy Engine](#13-strategy-engine)
14. [Next.js UI](#14-nextjs-ui)
15. [Docker Compose Overrides](#15-docker-compose-overrides)

---

## 1. Core Platform Variables

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `HOST_SERVER` | **Yes** | — | Public-facing domain with protocol (e.g., `https://trade.example.com`). Used for redirect URIs, CORS origins, and external links. |
| `APP_KEY` | **Yes** | — | Secret key for Flask session signing, CSRF token generation, and Fernet encryption. Generate with `python3 -c "import secrets; print(secrets.token_hex(32))"` (64 chars). |
| `API_KEY_PEPPER` | **Yes** | — | Second secret used to HMAC API keys before hashing (prevents rainbow table attacks even if DB is compromised). Generate the same way as `APP_KEY`. |
| `FLASK_ENV` | No | `production` | Flask environment mode. Set to `development` for verbose error pages and hot-reload. |
| `FLASK_DEBUG` | No | `False` | Enable Flask debug mode (auto-reload on file changes, interactive debugger on errors). **Never enable in production.** |
| `APP_MODE` | No | `standalone` | Deployment mode. `standalone` = runs behind reverse proxy. `railway` = auto-detects Railway env. |
| `SECRET_KEY` | No | `APP_KEY` | Explicit Flask secret key. Falls back to `APP_KEY` if not set. |

---

## 2. Broker Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `BROKER_API_KEY` | **Yes** | — | Your broker's API key (e.g., Zerodha API key, Angel Client ID). |
| `BROKER_API_SECRET` | **Yes** | — | Your broker's API secret. |
| `TOTP_SECRET` | No | — | Base32-encoded TOTP secret for 2FA broker login. |
| `TOTP_FIXED_CODE` | No | — | Static TOTP code for testing (bypasses actual 2FA). |
| `TOTP_FIXED_CODE_USER` | No | — | Username that can use the fixed TOTP code. |
| `REDIRECT_URL` | **Yes** | — | Broker OAuth callback URL (e.g., `https://trade.example.com/zerodha/callback`). |
| `LOGIN_URL` | No | — | Custom broker login URL (overrides default). |
| `LOGIN_TYPE` | No | — | Login type: `api_secret`, `totp`, `mobile`, `weblogin`. |
| `BROKER` | No | — | Default broker to use (e.g., `zerodha`, `angel`, `dhan`). |
| `ENABLE_ZERODHA` | No | `True` | Enable/disable Zerodha integration. |
| `ENABLE_ANGEL` | No | `True` | Enable/disable Angel Broking integration. |
| `ENABLE_DHAN` | No | `True` | Enable/disable Dhan integration. |
| `ENABLE_FLATTRADE` | No | `False` | Enable/disable Flattrade integration. |
| `ENABLE_MSTOCK` | No | `False` | Enable/disable MStock integration. |
| `ENABLE_SHUBHAM` | No | `False` | Enable/disable Shubharambh integration. |

---

## 3. Database Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATABASE_URL` | No | `sqlite:///db/silvertrade.db` | Production database connection string. Use PostgreSQL for production: `postgresql://user:pass@host:5432/silvertrade`. Falls back to SQLite for development. |
| `SQLALCHEMY_DATABASE_URI` | No | — | Explicit SQLAlchemy URI override. |
| `SQLALCHEMY_ENGINE_OPTIONS` | No | — | JSON string of SQLAlchemy engine options (pool size, echo, etc.). |
| `SQLALCHEMY_TRACK_MODIFICATIONS` | No | `False` | Disable Flask-SQLAlchemy event system (saves memory). |
| `DB_POOL_SIZE` | No | `10` | Connection pool size for PostgreSQL. |
| `DB_MAX_OVERFLOW` | No | `20` | Maximum overflow connections beyond pool size. |
| `DB_POOL_TIMEOUT` | No | `30` | Connection pool timeout in seconds. |
| `DB_POOL_RECYCLE` | No | `1800` | Recycle connections after this many seconds (prevents stale connections). |
| `DB_ECHO` | No | `False` | Log all SQL queries (development only). |
| `DATABASE_BACKUP_ENABLED` | No | `False` | Enable automatic database backups. |
| `DATABASE_BACKUP_INTERVAL` | No | `3600` | Backup interval in seconds. |
| `DATABASE_BACKUP_DIR` | No | `db/backups` | Directory for database backups. |
| `HISTORIFY_DB_PATH` | No | `db/historify.duckdb` | Path for DuckDB historify database. |
| `HEALTH_DB_PATH` | No | `db/health.db` | Path for health metrics database. |
| `SANDBOX_DB_PATH` | No | `db/sandbox.db` | Path for sandbox/paper trading database. |

### PostgreSQL Connection Examples

```bash
# Local PostgreSQL
DATABASE_URL=postgresql://silvertrade:password@localhost:5432/silvertrade

# Docker Compose (internal network)
DATABASE_URL=postgresql://silvertrade:password@postgres:5432/silvertrade

# Managed Cloud (Railway, Render, AWS RDS)
DATABASE_URL=postgresql://user:password@host.cloud.com:5432/silvertrade?sslmode=require
```

---

## 4. Redis Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `REDIS_URL` | No | `redis://localhost:6379/0` | Redis connection string. Required for session store, rate limiting, and caching in production. |
| `REDIS_HOST` | No | `localhost` | Redis host (used if `REDIS_URL` is not set). |
| `REDIS_PORT` | No | `6379` | Redis port. |
| `REDIS_PASSWORD` | No | — | Redis password (if using AUTH). |
| `REDIS_DB` | No | `0` | Redis database number. |
| `REDIS_SESSION_DB` | No | `1` | Redis database for Flask sessions. |
| `REDIS_CACHE_DB` | No | `2` | Redis database for cache. |
| `REDIS_RATE_LIMIT_DB` | No | `3` | Redis database for rate limiting. |
| `REDIS_SOCKET_TIMEOUT` | No | `5` | Redis socket timeout in seconds. |
| `REDIS_SOCKET_CONNECT_TIMEOUT` | No | `5` | Redis connection timeout in seconds. |
| `REDIS_MAX_CONNECTIONS` | No | `50` | Maximum Redis connection pool size. |
| `REDIS_SSL` | No | `False` | Enable SSL for Redis connection (use with Redis Cloud). |

---

## 5. WebSocket Configuration

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `WEBSOCKET_URL` | No | — | External WebSocket URL for clients (e.g., `wss://trade.example.com/ws`). |
| `WEBSOCKET_HOST` | No | `127.0.0.1` | WebSocket server bind address. Use `0.0.0.0` for Railway/Docker. |
| `WEBSOCKET_PORT` | No | `8765` | WebSocket proxy port (internal). |
| `WEBSOCKET_SSL` | No | `False` | Enable SSL for WebSocket (handled by nginx in production). |
| `SOCKETIO_MESSAGE_QUEUE` | No | — | Socket.IO message queue URL (Redis for multi-process). |
| `SOCKETIO_PATH` | No | `socket.io` | Socket.IO path. |
| `SOCKETIO_CORS_ALLOWED_ORIGINS` | No | — | Comma-separated CORS origins for Socket.IO. |
| `ZMQ_SUBSCRIBE_HOST` | No | `127.0.0.1` | ZeroMQ subscriber bind address. |
| `ZMQ_SUBSCRIBE_PORT` | No | `5555` | ZeroMQ subscriber port for market data feed. |
| `ZMQ_PUBLISH_HOST` | No | `127.0.0.1` | ZeroMQ publisher bind address. |
| `ZMQ_PUBLISH_PORT` | No | `5556` | ZeroMQ publisher port. |

---

## 6. Security & Authentication

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SESSION_COOKIE_SECURE` | No | `True` | Set Secure flag on session cookies (requires HTTPS). |
| `SESSION_COOKIE_HTTPONLY` | No | `True` | Set HttpOnly flag (prevents JavaScript access). |
| `SESSION_COOKIE_SAMESITE` | No | `Lax` | SameSite policy: `Lax`, `Strict`, or `None`. |
| `PERMANENT_SESSION_LIFETIME` | No | `14400` | Session lifetime in seconds (default: 4 hours). |
| `SESSION_TYPE` | No | `filesystem` | Session backend: `filesystem`, `redis`, `sqlalchemy`. |
| `SESSION_KEY_PREFIX` | No | `sess:` | Prefix for Redis session keys. |
| `SESSION_USE_SIGNER` | No | `True` | Sign session cookies for integrity. |
| `WTF_CSRF_ENABLED` | No | `True` | Enable CSRF protection on all POST/PUT/DELETE requests. |
| `WTF_CSRF_TIME_LIMIT` | No | `3600` | CSRF token time limit in seconds. |
| `CSP_DEFAULT_SRC` | No | `'self'` | Content Security Policy default source. |
| `CSP_SCRIPT_SRC` | No | `'self' 'unsafe-inline' 'unsafe-eval'` | CSP script sources (next.js needs inline). |
| `CSP_STYLE_SRC` | No | `'self' 'unsafe-inline'` | CSP style sources. |
| `CSP_IMG_SRC` | No | `'self' data: https: blob:` | CSP image sources. |
| `CSP_CONNECT_SRC` | No | `'self' ws: wss:` | CSP connect sources (for WebSocket). |
| `CSP_FRAME_SRC` | No | `'self'` | CSP frame sources. |
| `CSP_REPORT_URI` | No | — | CSP violation report endpoint. |
| `AUTO_APPROVE_ORDERS` | No | `False` | Auto-approve orders without confirmation. **Use with caution.** |
| `AUTO_APPROVE_USERS` | No | — | Comma-separated list of users who bypass order approval. |
| `FORCE_APPROVAL` | No | `False` | Force admin approval for all orders. |
| `STATIC_IP_WHITELIST` | No | — | Comma-separated IPs allowed to trade (SEBI mandate). |
| `ENABLE_CORS` | No | `True` | Enable CORS headers. |
| `MAX_LOGIN_ATTEMPTS` | No | `5` | Max failed login attempts before lockout. |
| `LOGIN_LOCKOUT_DURATION` | No | `900` | Lockout duration in seconds (15 min). |

---

## 7. Rate Limiting

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `RATE_LIMIT_ENABLED` | No | `True` | Enable rate limiting globally. |
| `RATE_LIMIT_STORAGE` | No | `redis://localhost:6379/3` | Rate limit storage backend. Falls back to memory if Redis unavailable. |
| `RATE_LIMIT_DEFAULT` | No | `200 per day, 50 per hour` | Default rate limit for all routes. |
| `RATE_LIMIT_LOGIN` | No | `10 per minute` | Rate limit for login endpoint. |
| `RATE_LIMIT_API` | No | `100 per minute` | Rate limit for general API calls. |
| `RATE_LIMIT_ORDERS` | No | `30 per minute` | Rate limit for order placement. |
| `RATE_LIMIT_WEBSOCKET` | No | `100 per minute` | Rate limit for WebSocket connections. |
| `RATE_LIMIT_WEBHOOK` | No | `20 per minute` | Rate limit for webhook endpoints. |

---

## 8. CORS & CSP

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `CORS_ORIGINS` | No | `http://localhost:3000,http://127.0.0.1:3000` | Allowed CORS origins. |
| `CORS_METHODS` | No | `GET, POST, PUT, PATCH, DELETE, OPTIONS` | Allowed HTTP methods. |
| `CORS_HEADERS` | No | `Content-Type, Authorization, X-CSRF-Token` | Allowed CORS headers. |
| `CORS_SUPPORTS_CREDENTIALS` | No | `True` | Allow cookies in cross-origin requests. |
| `CORS_MAX_AGE` | No | `600` | CORS preflight cache duration in seconds. |
| `CSP_ENABLED` | No | `True` | Enable Content Security Policy headers. |
| `CSP_REPORT_ONLY` | No | `False` | CSP report-only mode (log violations, don't block). |

---

## 9. Logging

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `LOG_LEVEL` | No | `INFO` | Logging level: `DEBUG`, `INFO`, `WARNING`, `ERROR`, `CRITICAL`. |
| `LOG_FILE` | No | — | Path to log file. If empty, logs go to stdout. |
| `LOG_FORMAT` | No | `json` | Log format: `json` (structured), `text` (human-readable). |
| `LOG_MAX_BYTES` | No | `10485760` | Max log file size before rotation (10 MB). |
| `LOG_BACKUP_COUNT` | No | `5` | Number of rotated log files to keep. |
| `LOG_SQL_QUERIES` | No | `False` | Log all SQL queries (development only). |
| `LOG_HTTP_REQUESTS` | No | `False` | Log all HTTP requests. |
| `LOG_HEARTBEAT` | No | `True` | Log periodic health check pings. |
| `TRAFFIC_LOG_ENABLED` | No | `False` | Enable traffic logging (request/response bodies). |
| `TRAFFIC_LOG_PATH` | No | `logs/traffic.log` | Traffic log file path. |
| `SENTRY_DSN` | No | — | Sentry DSN for error tracking. |
| `SENTRY_ENABLED` | No | `False` | Enable Sentry error reporting. |

---

## 10. Monitoring & Alerting

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SLACK_WEBHOOK_URL` | No | — | Slack incoming webhook URL for alert notifications. Format: `https://hooks.slack.com/services/T00/B00/xxxxx`. |
| `PAGERDUTY_ROUTING_KEY` | No | — | PagerDuty Events API v2 integration key. |
| `WEBHOOK_URL` | No | — | Generic webhook URL for custom alert automation. |
| `GRAFANA_USER` | No | `admin` | Grafana admin username. |
| `GRAFANA_PASSWORD` | No | `silvertrade` | Grafana admin password. **Change in production.** |
| `PROMETHEUS_RETENTION` | No | `30d` | Prometheus metrics retention period. |
| `METRICS_ENABLED` | No | `True` | Enable Prometheus metrics endpoint (`/metrics`). |

---

## 11. Service Discovery

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `DATA_FETCH_URL` | No | `http://data_fetch:5005` | Internal URL for Data Fetch service. |
| `TRADE_STRATEGIES_URL` | No | `http://trade_strategies:5007` | Internal URL for Strategy Engine. |
| `PLATFORM_URL` | No | `http://platform:5000` | Internal URL for Platform API (used by other services). |
| `NGINX_HOST` | No | — | Nginx upstream hostname (auto-detected in Docker). |
| `NGINX_PORT` | No | `80` | Nginx upstream port. |

---

## 12. Data Fetch Service

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SILVERTRADE_API_KEY` | **Yes** | — | Platform API key for data_fetch service authentication. |
| `SILVERTRADE_HOST` | **Yes** | `http://platform:5000` | Platform API base URL. |
| `FLASK_HOST` | No | `0.0.0.0` | Flask bind address. |
| `FLASK_PORT` | No | `5005` | Flask listen port. |
| `FLASK_DEBUG` | No | `False` | Enable debug mode. |
| `FLASK_ENV` | No | `production` | Flask environment. |

---

## 13. Strategy Engine

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `SILVERTRADE_API_KEY` | **Yes** | — | Platform API key for strategy engine authentication. |
| `SILVERTRADE_HOST` | **Yes** | `http://platform:5000` | Platform API base URL. |
| `FLASK_HOST` | No | `0.0.0.0` | Flask bind address. |
| `FLASK_PORT` | No | `5007` | Flask listen port. |
| `FLASK_DEBUG` | No | `False` | Enable debug mode. |

---

## 14. Next.js UI

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `NEXT_PUBLIC_API_URL` | **Yes** | — | Public-facing Platform API URL (e.g., `https://trade.example.com/api/v1`). |
| `NEXT_PUBLIC_WS_URL` | **Yes** | — | Public-facing WebSocket URL (e.g., `wss://trade.example.com/ws`). |
| `NODE_ENV` | No | `production` | Node.js environment. |

---

## 15. Docker Compose Overrides

Set these in your shell or `.env` file before running `docker compose`:

| Variable | Required | Default | Description |
|----------|----------|---------|-------------|
| `POSTGRES_PASSWORD` | No | `silvertrade` | PostgreSQL superuser password. **Change in production.** |
| `TAG` | No | `latest` | Docker image tag for custom builds. |

---

## Quick Reference: Required vs Optional

### Required for Production

```bash
# You MUST set these before deploying:
HOST_SERVER=https://trade.example.com
APP_KEY=<64-char-hex>
API_KEY_PEPPER=<64-char-hex>
BROKER_API_KEY=your_broker_key
BROKER_API_SECRET=your_broker_secret
REDIRECT_URL=https://trade.example.com/zerodha/callback
SILVERTRADE_API_KEY=your_platform_api_key
```

### Strongly Recommended

```bash
# These are optional but highly recommended:
POSTGRES_PASSWORD=<strong-password>
GRAFANA_PASSWORD=<strong-password>
SLACK_WEBHOOK_URL=https://hooks.slack.com/services/...
PAGERDUTY_ROUTING_KEY=your_pagerduty_key
DATABASE_URL=postgresql://silvertrade:password@postgres:5432/silvertrade
REDIS_URL=redis://redis:6379/0
LOG_LEVEL=INFO
```

### Secrets Generation

```bash
# Generate all required secrets:
python3 -c "
import secrets
print(f'APP_KEY: {secrets.token_hex(32)}')
print(f'API_KEY_PEPPER: {secrets.token_hex(32)}')
print(f'POSTGRES_PASSWORD: {secrets.token_urlsafe(24)}')
print(f'GRAFANA_PASSWORD: {secrets.token_urlsafe(16)}')
print(f'PLATFORM_API_KEY: st_{secrets.token_urlsafe(24)}')
"
```
