# SilverTrade AI — Architecture Overview

SilverTrade AI is a modular, microservice-based trading platform that combines real-time market data, AI-powered strategy analysis, and a modern web dashboard behind a unified API gateway.

---

## 1. System Architecture

```
┌──────────┐  ┌──────────┐  ┌───────────┐  ┌───────────┐
│          │  │          │  │           │  │           │
│  Browser │  │  Mobile  │  │  Trading  │  │  Telegram │
│  (Next.js│  │  Apps    │  │  View     │  │  Bot      │
│   UI)    │  │          │  │           │  │           │
└────┬─────┘  └────┬─────┘  └─────┬─────┘  └─────┬─────┘
     │              │              │               │
     └──────────────┴──────────────┴───────────────┘
                         │
                  ┌──────┴──────┐
                  │   Nginx     │  Port 443 (HTTPS) / 80 (HTTP)
                  │  Reverse    │  SSL termination, rate limiting
                  │  Proxy      │  Security headers, WebSocket proxy
                  └──────┬──────┘
                         │
          ┌──────────────┼──────────────────┐
          │              │                  │
   ┌──────┴──────┐  ┌────┴────┐  ┌─────────┴────────┐
   │  Platform   │  │  Data   │  │     Strategy     │
   │  API        │  │  Fetch  │  │     Engine       │
   │  (Flask)    │  │ (Flask) │  │     (Flask)      │
   │  :5000      │  │ :5005   │  │     :5007        │
   └──────┬──────┘  └─────────┘  └──────────────────┘
          │
    ┌─────┴──────┐
    │  Next.js   │
    │  UI        │
    │  :3000     │
    └────────────┘

┌─────────────────────────────────────────────────────┐
│                 Docker Network                       │
│              172.x.x.x / silvertrade-net             │
└─────────────────────────────────────────────────────┘

   ┌──────────┐   ┌──────────┐   ┌──────────────────┐
   │PostgreSQL│   │  Redis   │   │  WebSocket Proxy │
   │  :5432   │   │  :6379   │   │  ZMQ :5555       │
   └──────────┘   └──────────┘   └──────────────────┘
```

---

## 2. Services

### 2.1 Platform API (Primary Service)

- **Framework:** Flask 3.x with Gunicorn + Eventlet
- **Port:** 5000 (internal)
- **Purpose:** API gateway for all trading operations
- **Key responsibilities:**
  - User authentication (session-based, TOTP 2FA)
  - Broker integration (30+ brokers via plugin architecture)
  - Order management (place, modify, cancel, smart orders)
  - Real-time WebSocket streaming for market data
  - Options analytics (Greeks, IV smile, volatility surface)
  - Python strategy execution engine
  - Telegram bot integration
  - RESTx API v1 with CSRF protection

### 2.2 Data Fetch Service

- **Framework:** Flask 3.x
- **Port:** 5005 (internal)
- **Purpose:** Historical market data aggregation and charting
- **Key features:**
  - OHLCV data fetching from platform API
  - Williams VIX Fix indicator calculation
  - TradingView Lightweight Charts integration
  - PineTS framework compatibility

### 2.3 Strategy Engine

- **Framework:** Flask 3.x
- **Port:** 5007 (internal)
- **Purpose:** AI-powered trading decision engine
- **Key features:**
  - Real technical indicators (SMA, EMA, RSI, MACD, Bollinger Bands, ATR)
  - 7-factor scoring system for trade signals
  - BUY/SELL/HOLD decisions with confidence scores
  - Mock data fallback when platform is unavailable
  - Thread-safe signal history

### 2.4 Next.js UI

- **Framework:** Next.js 16 with React 19
- **Port:** 3000 (internal)
- **Purpose:** Modern web dashboard
- **Key pages:**
  - Landing page with hero/features/pricing
  - Login/Signup with email or Google OAuth
  - Dashboard with portfolio, price chart, AI feed, alerts
  - Trading interface with order form, leverage, SL/TP
  - AI chat assistant for trading insights
  - Missed opportunities tracker

### 2.5 Nginx Reverse Proxy

- **Version:** 1.25 Alpine
- **Ports:** 80 (HTTP) → 443 (HTTPS)
- **Purpose:** SSL termination, routing, security
- **Key features:**
  - Automatic HTTP → HTTPS redirect
  - TLS 1.2/1.3 with Mozilla Intermediate cipher suite
  - HSTS (1 year + preload), security headers
  - Rate limiting per endpoint (API, auth, orders, webhooks)
  - WebSocket proxy support (86400s timeout)
  - Static asset caching (30d)
  - Route to all microservices

---

## 3. Data Flow

### 3.1 Trade Execution Flow

```
User → Nginx → Platform API → Broker Plugin → Exchange
  ↑                          │
  └── WebSocket ←─── ZMQ ←──┘
```

1. User places order via UI or API
2. Nginx terminates SSL, rate-limits, routes to Platform
3. Platform authenticates, validates, routes to broker plugin
4. Broker plugin translates to exchange-specific API
5. Order status streamed back via WebSocket proxy

### 3.2 AI Signal Generation Flow

```
Data Fetch → Platform → Strategy Engine → UI
                    ↘                      ↙
                  PostgreSQL (signal history)
```

1. Strategy Engine fetches OHLCV data via Platform API
2. Engine calculates 7+ technical indicators
3. Scoring system produces BUY/SELL/HOLD decision
4. Signal stored in memory, exposed via REST API
5. UI polls `/api/v1/signals` and displays in AI Feed

---

## 4. Broker Plugin Architecture

The platform supports 30+ brokers through a plugin-based architecture:

```
broker/
├── angel/          # Angel Broking
├── zerodha/        # Zerodha (Kite)
├── binance/        # Binance (Crypto)
├── deltaexchange/  # Delta Exchange (Crypto)
├── bybit/          # Bybit (Crypto)
├── upstox/         # Upstox
├── dhan/           # Dhan
├── fivepaisa/      # 5Paisa
└── ...             # 22+ more brokers
```

Each broker plugin follows a standard structure:

```
broker/<name>/
├── __init__.py
├── plugin.json          # Metadata (name, capabilities)
├── api/
│   ├── auth_api.py      # Authentication
│   ├── order_api.py     # Order management
│   ├── data.py          # Market data
│   └── funds.py         # Balance/funds
├── mapping/
│   ├── order_data.py    # Data normalization
│   └── transform_data.py# Format transformation
├── streaming/
│   ├── websocket_client.py
│   ├── <broker>_adapter.py
│   └── <broker>_mapping.py
└── database/
    └── master_contract_db.py
```

---

## 5. Monitoring Architecture

```
┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│  node-exporter│    │   cAdvisor   │    │  PostgreSQL  │
│  (Host)      │    │ (Containers) │    │  Exporter    │
└──────┬───────┘    └──────┬───────┘    └──────┬───────┘
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                    ┌──────┴──────┐
                    │  Prometheus │
                    │  :9090      │
                    └──────┬──────┘
                           │
            ┌──────────────┼──────────────┐
            │              │              │
     ┌──────┴──────┐ ┌────┴────┐  ┌──────┴──────┐
     │  Grafana    │ │AlertMgr │  │  Thanos     │
     │  :3001      │ │ :9093   │  │  (optional) │
     └─────────────┘ └─────────┘  └─────────────┘
                           │
                    ┌──────┴──────┐
                    │   Slack /   │
                    │  PagerDuty  │
                    └─────────────┘
```

---

## 6. Security Architecture

- **Authentication:** Session cookies with HttpOnly + Secure + SameSite=Lax, CSRF tokens
- **Password hashing:** Argon2 via Flask-Bcrypt
- **2FA:** TOTP (Time-based One-Time Password) via PyOTP
- **Broker tokens:** Encrypted at rest using Fernet symmetric encryption
- **API keys:** Hashed with API_KEY_PEPPER before storage
- **HTTPS:** Mandatory in production, HSTS 1 year + preload
- **CSP:** Content Security Policy headers on all responses
- **Rate limiting:** Per-endpoint (login, API, orders, webhooks)
- **Session expiry:** Automatic at 3:30 AM IST (configurable)
- **Reverse proxy trust:** Configurable for Cloudflare/nginx behind proxy

---

## 7. Database Architecture

| Database | Type | Purpose |
|----------|------|---------|
| `silvertrade.db` | SQLite/PostgreSQL | Auth, orders, positions, settings |
| `latency.db` | SQLite | API latency monitoring |
| `logs.db` | SQLite | Traffic logs |
| `health.db` | SQLite | Health monitoring metrics |
| `sandbox.db` | SQLite | Sandbox/analyzer mode |
| `historify.duckdb` | DuckDB | Historical OHLCV data |

**Production:** Use PostgreSQL (recommended) via `DATABASE_URL` env var.

---

## 8. Technology Stack

| Component | Technology |
|-----------|------------|
| Backend | Python 3.12+, Flask 3.x |
| API Framework | Flask-RESTx |
| ASGI/WSGI | Gunicorn + Eventlet |
| Database ORM | SQLAlchemy 2.x |
| Frontend | Next.js 16, React 19, TypeScript |
| UI Components | shadcn/ui, Tailwind CSS 4 |
| Charts | Lightweight Charts, Recharts |
| WebSocket | Flask-SocketIO, python-socketio |
| Message Bus | ZeroMQ (internal broker feed) |
| Caching | Redis 7 |
| Database | PostgreSQL 16 / SQLite / DuckDB |
| Container | Docker, Docker Compose |
| Reverse Proxy | Nginx 1.25 |
| Monitoring | Prometheus, Grafana, cAdvisor |
| Alerting | AlertManager (Slack, PagerDuty) |
| SSL | Let's Encrypt (Certbot) |
