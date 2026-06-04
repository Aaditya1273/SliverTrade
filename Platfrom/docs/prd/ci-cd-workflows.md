# SilverTrade AI — CI/CD Workflows Reference

## Overview

This document details all GitHub Actions workflows in the SilverTrade AI CI/CD pipeline.

### Workflows at a Glance

| Workflow | File | Trigger | Description |
|----------|------|---------|-------------|
| **Main CI/CD** | `.github/workflows/ci.yml` | Push to main/develop, PR to main, labels | Full pipeline: quality → tests → build → deploy |
| **Security Audit** | `.github/workflows/security.yml` | Weekly schedule (Monday 2:30 AM IST) | Comprehensive security analysis |
| **Dependabot** | `.github/dependabot.yml` | Monday weekly | Automated dependency update PRs |

---

## 1. Main CI/CD Pipeline

**File:** `.github/workflows/ci.yml`

### Triggers

| Event | Condition | What Runs |
|-------|-----------|-----------|
| `push` to `main` | — | Full pipeline: lint → test → build → staging deploy |
| `push` to `develop` | — | Quality checks + tests only |
| `pull_request` to `main` | — | Quality checks + tests only |
| `pull_request` labeled `deploy:staging` | — | Build + staging deploy |
| `pull_request` labeled `deploy:production` | — | Build only (production deploy requires commit message) |
| Commit message contains `[deploy:production]` | Push to `main` | Full pipeline + production deploy |

**Concurrency:** Cancels in-progress runs when new commits are pushed to the same branch.

### Job Dependency Graph

```
                    ┌─────────────┐
                    │  lint       │
                    ├─────────────┤
                    │  type-check │
                    ├─────────────┤
                    │  security   │
                    ├─────────────┤
                    │  frontend-  │
                    │  lint       │
                    └──────┬──────┘
                           │
                           ▼
               ┌─────────────────────┐
               │  test-python        │
               │  (PostgreSQL+Redis) │
               └──────────┬──────────┘
                          │
              ┌───────────┴───────────┐
              │                       │
              ▼                       ▼
   ┌────────────────────┐  ┌──────────────────────┐
   │ build-docker (x5)  │  │ validate-deploy-      │
   │ Platform, Data     │  │ scripts              │
   │ Fetch, Strategy,   │  │ Shell syntax check    │
   │ UI, AlertManager   │  │ Compose syntax check  │
   │ + Trivy scan       │  │ Nginx config check    │
   └──────────┬─────────┘  └──────────┬───────────┘
              │                       │
              └───────────┬───────────┘
                          │
                          ▼
         ┌──────────────────────────────┐
         │  deploy-staging              │
         │  (auto on main merge)        │
         │  Pre/post health checks      │
         └──────────────────────────────┘

         ┌──────────────────────────────┐
         │  deploy-production           │
         │  (manual approval gate)      │
         │  Zero-downtime rolling       │
         │  Slack notifications         │
         └──────────────────────────────┘

                              ┌──────────────────────┐
                              │  notify-failure      │
                              │  Slack on main fail  │
                              └──────────────────────┘
```

### Jobs Detail

#### 1.1 Quality Checks (Parallel, ~30s each)

| Job | Tool | Purpose | Failure Action |
|-----|------|---------|----------------|
| `lint` | Ruff | Python lint + format | `uv run ruff check . --fix && uv run ruff format .` |
| `type-check` | mypy | Python type safety | Fix type annotations |
| `security-scan` | Bandit + pip-audit | SAST + dependency vulns | Fix issues or add ignore rules |
| `frontend-lint` | ESLint + TypeScript | JS/TS code quality | `npm run lint && npx tsc --noEmit` |

#### 1.2 Tests (After Quality Checks, ~2min)

**`test-python`** — Runs pytest with PostgreSQL and Redis service containers:

```bash
uv run pytest test/ -v --timeout=120 -x --tb=short
```

- Database: SQLite (in-memory for speed)
- Redis: GitHub Actions service container
- Env vars injected for CI-safe test execution
- Coverage artifact uploaded (7-day retention)

**`frontend-lint`** blocks both test and build stages — no separate frontend test job since the CI focuses on lint/type-check for the UI.

#### 1.3 Build & Scan (After Tests, ~3min per image × 5 = ~15min total)

**`build-docker`** — Matrix build of 5 Docker images:

| Service | Context | Tags |
|---------|---------|------|
| `platform` | `./Platfrom` | `:sha-xxxx`, `:main`, `:latest` |
| `data-fetch` | `./data_fetch` | `:sha-xxxx`, `:main`, `:latest` |
| `strategy-engine` | `./Trade_Strategies` | `:sha-xxxx`, `:main`, `:latest` |
| `ui` | `./ui` | `:sha-xxxx`, `:main`, `:latest` |
| `alertmanager` | `./monitoring/alertmanager` | `:sha-xxxx`, `:main`, `:latest` |

Each image is:
1. Built with Docker Buildx (GHA cache for speed)
2. Pushed to GitHub Container Registry (`ghcr.io`)
3. Scanned with **Trivy** for CRITICAL/HIGH vulnerabilities
4. SARIF report uploaded to GitHub Security tab

**Trivy fails the build** if any CRITICAL or HIGH vulnerability is found (excluding `./app/.venv` Python packages, which are covered by pip-audit separately).

#### 1.4 Deploy Script Validation (After Tests, ~15s)

**`validate-deploy-scripts`** — Validates infrastructure code:

- Shell syntax check: `bash -n deploy/*.sh`
- Docker Compose syntax: `docker compose -f <file> config`
- Nginx config validity: `nginx -t`

#### 1.5 Staging Deploy (Auto on main merge)

**`deploy-staging`** — Deploys to staging environment:

```
Step 1: Pre-deploy health check (verify current stack is running)
Step 2: Pull latest images from GHCR
Step 3: Start services with --remove-orphans
Step 4: Wait 15s for health checks
Step 5: Post-deploy verification (health-check.sh --verbose)
Step 6: Clean up old images (prune -f --filter "until=24h")
```

**Environment:** `staging` — GitHub Environment with optional reviewers.

#### 1.6 Production Deploy (Manual Approval)

**`deploy-production`** — Zero-downtime production deployment:

**Trigger requirement:** Commit message contains `[deploy:production]`.

```
Step 1: Slack notification → deployment starting
Step 2: Pre-deploy health check (JSON output)
Step 3: Pull latest production images
Step 4: Rolling update with scale-up/scale-down:
         docker compose up -d --scale platform=2  # Run 2 instances
         sleep 30  # Wait for health checks
         docker compose up -d --scale platform=1  # Scale back
Step 5: Post-deploy verification
Step 6: Clean up old images
Step 7: Slack notification → success/failure
```

**Environment:** `production` — Requires manual approval from a designated reviewer via GitHub Environments. Deploy job will not proceed until approved.

**Required secrets:**
- `PRODUCTION_SSH_KEY` — SSH private key for prod server
- `PRODUCTION_HOST` — Production server hostname
- `PRODUCTION_USER` — SSH user
- `SLACK_DEPLOY_WEBHOOK` — Slack webhook for deploy notifications

#### 1.7 Failure Notifications (Slack)

**`notify-failure`** — Sends Slack notification to `#deployments` when CI fails on `main` branch. Runs regardless of which job failed.

**Required secret:** `SLACK_DEPLOY_WEBHOOK`

---

## 2. Security Audit Workflow

**File:** `.github/workflows/security.yml`

### Triggers

- **Schedule:** Every Monday at 2:30 AM IST (Sunday 21:00 UTC)
- **Manual:** `workflow_dispatch` from GitHub Actions UI

### Jobs

| Job | Tool | Purpose | Artifact |
|-----|------|---------|----------|
| `sast-python` | Bandit (SARIF) | Deep SAST scan | Uploaded to GitHub Security tab |
| `dependency-audit` | pip-audit (matrix) | 3 services scanned | JSON reports (30-day retention) |
| `secrets-scan` | detect-secrets | Credential leak detection | JSON report (30-day retention) |
| `npm-audit` | npm audit | Frontend vulns | JSON report (30-day retention) |
| `security-summary` | — | Consolidated report | Job summary in GitHub UI |

All jobs use `continue-on-error` — findings are informational and will never block the workflow. Review the generated reports and GitHub Security tab for actionable items.

### Viewing Results

1. **GitHub Security Tab:** SAST results appear in `https://github.com/<org>/<repo>/security/code-scanning`
2. **Workflow Artifacts:** Download from workflow run page (retained 30 days)
3. **Job Summary:** The `security-summary` job generates a table in the workflow summary

---

## 3. Dependabot

**File:** `.github/dependabot.yml`

Automatically creates PRs for dependency updates across all ecosystems:

| Ecosystem | Directory | PR Limit | Groups |
|-----------|-----------|----------|--------|
| pip | `/Platfrom` | 10 | flask, sqlalchemy, testing, security |
| pip | `/data_fetch` | 5 | — |
| pip | `/Trade_Strategies` | 5 | — |
| npm | `/` | 3 | — |
| npm | `/ui` | 10 | react, radix, testing |
| docker | `/Platfrom` | 3 | — |
| docker | `/data_fetch` | 3 | — |
| docker | `/Trade_Strategies` | 3 | — |
| docker | `/ui` | 3 | — |
| github-actions | `/` | 5 | — |

**Grouping:** Minor and patch updates within the same ecosystem/group are batched into a single PR — reduces noise.

**Major updates** for `numpy`, `pandas`, and `scipy` are **ignored** (review manually — major Python data lib versions can be breaking).

**Labels:** All PRs are tagged with `dependencies` + ecosystem-specific label (`python`, `frontend`, `docker`, `ci`, `css`).

---

## 4. Required Secrets

Configure these in your GitHub repository: **Settings → Secrets and variables → Actions**

| Secret | Used By | Description |
|--------|---------|-------------|
| `STAGING_SSH_KEY` | CI (deploy-staging) | SSH private key for staging server |
| `STAGING_HOST` | CI (deploy-staging) | Staging server hostname |
| `STAGING_USER` | CI (deploy-staging) | SSH user for staging |
| `PRODUCTION_SSH_KEY` | CI (deploy-production) | SSH private key for production server |
| `PRODUCTION_HOST` | CI (deploy-production) | Production server hostname |
| `PRODUCTION_USER` | CI (deploy-production) | SSH user for production |
| `SLACK_DEPLOY_WEBHOOK` | CI (notifications) | Slack incoming webhook URL for deploy notifications |

---

## 5. Best Practices

### Commit Message Convention

```bash
# Regular commit — runs quality checks + tests
git commit -m "Fix order validation in place_order_service"

# Commit with production deploy — runs full pipeline
git commit -m "Add WebSocket reconnection logic [deploy:production]"
```

> **⚠️ Important:** The `[deploy:production]` marker must be in the **merge commit message**, not in individual PR commits. When merging a PR, GitHub uses the PR title + number as the merge commit message (`Merge pull request #123 from user/branch`). To trigger production deploy:
> - **Option A (recommended):** Use **Squash and merge** — the squash commit message preserves all content including `[deploy:production]`.
> - **Option B:** Edit the merge commit message to include `[deploy:production]` before confirming the merge.
> - **Option C:** After merge, push an empty commit: `git commit --allow-empty -m "Trigger production deploy [deploy:production]" && git push`

### PR Label Convention

| Label | Effect |
|-------|--------|
| `deploy:staging` | Build Docker images + deploy to staging |
| `deploy:production` | Build Docker images (production deploy requires commit message) |

### Local Development Commands

```bash
# Run the same checks as CI
uv run ruff check . && uv run ruff format --check .
uv run mypy .
uv run pytest test/ -v --timeout=120

# Validate infrastructure
bash -n deploy/deploy.sh
docker compose -f docker-compose.prod.yml config
docker run --rm -v $(pwd)/nginx:/etc/nginx:ro nginx:1.25-alpine nginx -t
```

---

## 6. Troubleshooting

### CI is slow

1. Check cache hit rate in job logs — cold caches add 2-3min per build
2. Ensure `uv.lock`, `package-lock.json`, and `requirements.txt` are committed
3. Docker Buildx cache (`type=gha`) requires the GHA cache to warm up on first run

### Trivy scan fails the build

```bash
# Scan locally to see what's flagged
docker build -t silvertrade-platform ./Platfrom
trivy image --severity CRITICAL,HIGH silvertrade-platform
```

If a false positive, add a `.trivyignore` file:
```yaml
# .trivyignore
CVE-2024-XXXXX: False positive — only affects Python <3.11, we use 3.12
```

### Docker build fails with "no space left"

```bash
# Free up space on the runner
docker system prune -f
```

### Staging deploy fails

Check the SSH connection:
```bash
ssh -i ~/.ssh/id_ed25519 user@host "docker compose -f docker-compose.staging.yml ps"
```
