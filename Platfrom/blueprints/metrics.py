"""
SilverTrade AI — Prometheus Metrics Exporter
==============================================
Wraps prometheus_flask_exporter to auto-instrument all HTTP routes
and expose metrics at /metrics for Prometheus scraping.

Usage in app.py:
    from blueprints.metrics import init_metrics
    init_metrics(app)

Requires: pip install prometheus_flask_exporter
"""

from prometheus_flask_exporter import PrometheusMetrics

from utils.logging import get_logger

logger = get_logger(__name__)

_metrics_instance = None


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
