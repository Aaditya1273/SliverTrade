"""
SilverTrade AI — Prometheus Metrics Exporter
==============================================
Wraps prometheus_flask_exporter to auto-instrument all HTTP routes
and expose metrics at /metrics for Prometheus scraping.

Usage in app.py:
    from blueprints.metrics import init_metrics
    init_metrics(app)

Requires: pip install prometheus_flask_exporter

Custom metrics (registered globally so any module can use them):

    ``broker_api_requests_total`` — Counter, labelled by broker / method / status
    ``broker_api_latency_seconds`` — Histogram, labelled by broker / method
    ``circuit_breaker_info`` — Gauge (0/1/2 = CLOSED/HALF_OPEN/OPEN), per breaker
    ``active_ws_connections`` — Gauge, labelled by broker
    ``db_pool_usage`` — Gauge, labelled by db_name
"""

from prometheus_flask_exporter import PrometheusMetrics

from utils.logging import get_logger

logger = get_logger(__name__)

_metrics_instance = None

# ── Custom Prometheus Metrics ───────────────────────────────────────────
# Defined at module level so they can be imported and used by any module
# (httpx_client.py, circuit_breaker.py, etc.) without coupling to Flask.

_broker_requests = None
_broker_latency = None
_circuit_breaker_gauge = None
_ws_connections_gauge = None
_db_pool_gauge = None


def _register_custom_metrics():
    """Register custom Prometheus metrics.  Called once during init_metrics."""
    global _broker_requests, _broker_latency, _circuit_breaker_gauge
    global _ws_connections_gauge, _db_pool_gauge

    try:
        from prometheus_client import Counter, Gauge, Histogram

        _broker_requests = Counter(
            "broker_api_requests_total",
            "Total broker API requests",
            ["broker", "method", "status"],
        )
        _broker_latency = Histogram(
            "broker_api_latency_seconds",
            "Broker API request latency in seconds",
            ["broker", "method"],
            buckets=(
                0.005,
                0.01,
                0.025,
                0.05,
                0.075,
                0.1,
                0.25,
                0.5,
                0.75,
                1.0,
                2.5,
                5.0,
                7.5,
                10.0,
                float("inf"),
            ),
        )
        _circuit_breaker_gauge = Gauge(
            "circuit_breaker_state",
            "Circuit breaker state (0=CLOSED, 1=HALF_OPEN, 2=OPEN)",
            ["breaker"],
        )
        _ws_connections_gauge = Gauge(
            "active_ws_connections",
            "Active WebSocket connections per broker",
            ["broker"],
        )
        _db_pool_gauge = Gauge(
            "db_pool_connections",
            "Database connection pool utilisation",
            ["db_name", "metric"],
        )

        logger.debug("Custom Prometheus metrics registered")
    except ImportError:
        logger.debug("prometheus_client not available — custom metrics disabled")
    except Exception as e:
        logger.warning(f"Failed to register custom metrics: {e}")


def broker_request_inc(broker: str, method: str, status: str | int) -> None:
    """Increment the broker API request counter."""
    if _broker_requests is not None:
        _broker_requests.labels(broker=broker, method=method.upper(), status=str(status)).inc()


def broker_latency_observe(broker: str, method: str, seconds: float) -> None:
    """Observe broker API latency."""
    if _broker_latency is not None:
        _broker_latency.labels(broker=broker, method=method.upper()).observe(seconds)


def circuit_breaker_set(breaker: str, state: str) -> None:
    """Set circuit breaker gauge.  ``state`` is CLOSED/HALF_OPEN/OPEN."""
    if _circuit_breaker_gauge is not None:
        value = {"CLOSED": 0, "HALF_OPEN": 1, "OPEN": 2}.get(state.upper(), 0)
        _circuit_breaker_gauge.labels(breaker=breaker).set(value)


def ws_connections_set(broker: str, count: int) -> None:
    """Set active WebSocket connections gauge."""
    if _ws_connections_gauge is not None:
        _ws_connections_gauge.labels(broker=broker).set(count)


def db_pool_set(db_name: str, metric: str, value: float) -> None:
    """Set database pool metric gauge."""
    if _db_pool_gauge is not None:
        _db_pool_gauge.labels(db_name=db_name, metric=metric).set(value)


def init_metrics(app):
    """Initialize the Prometheus metrics exporter on the Flask app.

    Call this during app creation to instrument all routes.
    The /metrics endpoint is auto-created by the exporter.
    """
    global _metrics_instance

    if _metrics_instance is not None:
        return _metrics_instance

    try:
        _metrics_instance = PrometheusMetrics(
            app,
            group_by="endpoint",
            defaults_prefix="flask",
        )

        _metrics_instance.info(
            "app_info",
            "SilverTrade AI Application Info",
            version="1.0.0",
        )

        # Register custom metrics after the exporter is ready
        _register_custom_metrics()

        logger.info("Prometheus metrics exporter initialized")
        return _metrics_instance

    except ImportError:
        logger.warning(
            "prometheus_flask_exporter not installed. "
            "Install it with: pip install prometheus_flask_exporter"
        )
        return None
    except Exception as e:
        logger.error(f"Failed to initialize metrics exporter: {e}")
        return None


def get_metrics():
    """Get the current metrics instance for custom metric registration."""
    return _metrics_instance
