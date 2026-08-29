# =============================================================================
# SilverTrade AI — Trade Strategies Dockerfile
# =============================================================================
# Python 3.12 base for PyTorch (LSTM) compatibility.
# Uses gunicorn as the production WSGI server — never run Flask's dev server
# in production.
#
# Build:
#   docker build -t silvertrade-strategies ./Trade_Strategies
#
# Run:
#   docker run -p 5007:5007 \
#     -e SILVERTRADE_HOST=http://platform:5000 \
#     silvertrade-strategies
# =============================================================================

FROM python:3.14-slim AS python-builder

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

WORKDIR /app

# Install Python dependencies (including gunicorn)
COPY requirements.txt .
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir \
        -r requirements.txt \
        "gunicorn>=25.0,<26" && \
    rm -rf /root/.cache

# ---------------------------------------------------------------------------
# Production Stage
# ---------------------------------------------------------------------------
FROM python:3.14-slim AS production

# Install runtime dependencies — BLAS/GCC libs for numpy/scikit-learn
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    libopenblas0 \
    libgomp1 \
    libgfortran5 \
    && apt-get clean && rm -rf /var/lib/apt/lists/*

# Create non-root user
RUN useradd --create-home appuser

WORKDIR /app

# Copy installed packages from builder
COPY --from=python-builder /usr/local/lib/python3.12/site-packages /usr/local/lib/python3.12/site-packages
COPY --from=python-builder /usr/local/bin /usr/local/bin

# Copy application source
COPY . .

# Ensure directories exist with correct permissions
RUN mkdir -p /app/log /app/ml/models && \
    chown -R appuser:appuser /app/log /app/ml/models

# ── Runtime environment ─────────────────────────────────────────────────────
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    STRATEGY_PORT=5007 \
    FLASK_ENV=production

USER appuser

EXPOSE 5007

# Healthcheck — pings the health endpoint every 30s
HEALTHCHECK --interval=30s --timeout=10s --retries=3 --start-period=15s \
    CMD curl -sf http://127.0.0.1:5007/api/v1/health || exit 1

# Use gunicorn.conf.py for all configuration.
# Operators can override any setting via environment variables
# (GUNICORN_WORKERS, GUNICORN_TIMEOUT, GUNICORN_BIND, etc.)
# without modifying the config file.
CMD ["gunicorn", "strategies_app:app", "--config", "gunicorn.conf.py"]
