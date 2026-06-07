"""
Health Monitoring Blueprint

Industry-standard health check endpoints:
- GET /health/status - Simple 200 OK for AWS ELB, K8s probes (unauthenticated)
- GET /health/check - DB connectivity + detailed status (unauthenticated)
- GET /health/api/* - Metrics API endpoints (authenticated)

Dashboard UI is served by React at /health (see frontend/src/pages/HealthMonitor.tsx)

Follows draft-inadarei-api-health-check-06 specification.
ZERO LATENCY IMPACT - all metrics collected in background thread.
"""

import csv
import io
from datetime import datetime

import pytz
from flask import Blueprint, Response, jsonify, request

from database.health_db import HealthAlert, HealthMetric, health_session
from limiter import limiter
from utils.health_monitor import get_cached_health_status
from utils.logging import get_logger
from utils.session import check_session_validity

logger = get_logger(__name__)

health_bp = Blueprint("health_bp", __name__, url_prefix="/health")


def convert_to_ist(timestamp):
    """Convert UTC timestamp to IST"""
    if isinstance(timestamp, str):
        timestamp = datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
    utc = pytz.timezone("UTC")
    ist = pytz.timezone("Asia/Kolkata")
    if timestamp.tzinfo is None:
        timestamp = utc.localize(timestamp)
    return timestamp.astimezone(ist)


def format_ist_time(timestamp):
    """Format timestamp in IST with 12-hour format"""
    ist_time = convert_to_ist(timestamp)
    return ist_time.strftime("%d-%m-%Y %I:%M:%S %p")


# ============================================================================
# Simple Health Checks (for AWS ELB, K8s, Docker, monitoring tools)
# ============================================================================


@health_bp.route("/status", methods=["GET"])
@limiter.limit("300/minute")  # High limit for load balancer polling
def simple_health():
    """
    Simple health check endpoint for AWS ELB, Kubernetes probes, Docker healthcheck.
    Returns instant 200 OK if service is running.

    Use /health/status for load balancers (unauthenticated JSON response).
    Use /health for the React dashboard UI.

    This endpoint uses cached metrics (ZERO latency impact).
    Does not require authentication.

    Response format follows draft-inadarei-api-health-check:
    {
        "status": "pass"|"warn"|"fail",
        "version": "1.0",
        "releaseId": "...",
        "serviceId": "silvertrade"
    }
    """
    try:
        # Liveness check: always 200 if the server is running and responding
        # Returns pass as long as the process is alive.
        # Detailed health checks with DB status go to /health/check.
        return (
            jsonify(
                {
                    "status": "pass",
                    "version": "1.0",
                    "serviceId": "silvertrade",
                    "description": "SilverTrade Trading Platform",
                }
            ),
            200,
        )
    except Exception as e:
        logger.error(f"Error in simple health check: {e}")
        return jsonify({"status": "fail", "description": str(e)}), 503


@health_bp.route("/check", methods=["GET"])
@limiter.limit("60/minute")
def detailed_health_check():
    """
    Detailed health check with component status.
    Includes database connectivity checks.

    Suitable for monitoring tools that need detailed status.
    Does not require authentication.

    Response format follows draft-inadarei-api-health-check:
    {
        "status": "pass"|"warn"|"fail",
        "version": "1.0",
        "serviceId": "silvertrade",
        "checks": {
            "database:connectivity": [{
                "componentId": "silvertrade",
                "status": "pass"|"fail",
                "time": "2026-01-30T10:15:30Z"
            }],
            "system:file-descriptors": [{
                "componentId": "fd_count",
                "status": "pass"|"warn"|"fail",
                "observedValue": 156,
                "observedUnit": "count"
            }],
            ...
        }
    }
    """
    try:
        # Use cached metrics — no synchronous DB calls that block under load
        cached_status = get_cached_health_status()
        db_check = cached_status.get("database", {"status": "pass"})
        if isinstance(db_check, dict) and "databases" not in db_check:
            db_check = {"status": db_check.get("status", "pass"), "databases": {"all": db_check.get("status", "pass")}}

        # Get current metrics from cache
        current_metric = HealthMetric.get_current_metrics()

        checks = {}

        # Database connectivity checks
        if db_check and "databases" in db_check:
            checks["database:connectivity"] = []
            for db_name, status in db_check["databases"].items():
                checks["database:connectivity"].append(
                    {
                        "componentId": db_name,
                        "status": status,
                        "time": datetime.utcnow().isoformat() + "Z",
                    }
                )

        # File descriptor checks
        if current_metric and current_metric.fd_count is not None:
            checks["system:file-descriptors"] = [
                {
                    "componentId": "fd_count",
                    "status": current_metric.fd_status or "pass",
                    "observedValue": current_metric.fd_count,
                    "observedUnit": "count",
                    "time": current_metric.timestamp.isoformat() + "Z"
                    if current_metric.timestamp
                    else None,
                }
            ]

        # Memory checks
        if current_metric and current_metric.memory_rss_mb is not None:
            checks["system:memory"] = [
                {
                    "componentId": "rss",
                    "status": current_metric.memory_status or "pass",
                    "observedValue": round(current_metric.memory_rss_mb, 2),
                    "observedUnit": "MiB",
                    "time": current_metric.timestamp.isoformat() + "Z"
                    if current_metric.timestamp
                    else None,
                }
            ]

        # Include WebSocket proxy resource health if available (best-effort)
        try:
            from websocket_proxy import get_resource_health

            ws_health = get_resource_health()
            checks["websocket:proxy"] = [
                {
                    "componentId": "websocket_proxy",
                    "status": "pass",
                    "observedValue": ws_health.get("active_pools", {}).get("count", 0),
                    "observedUnit": "count",
                    "time": datetime.utcnow().isoformat() + "Z",
                }
            ]
        except Exception:
            pass

        # Overall status (worst of all checks)
        overall_status = "pass"
        if db_check["status"] == "fail":
            overall_status = "fail"
        elif cached_status["status"] == "fail":
            overall_status = "fail"
        elif cached_status["status"] == "warn" or db_check["status"] == "warn":
            overall_status = "warn"

        status_code = 200
        if overall_status == "fail":
            status_code = 503

        return (
            jsonify(
                {
                    "status": overall_status,
                    "version": "1.0",
                    "serviceId": "silvertrade",
                    "description": "SilverTrade Trading Platform",
                    "checks": checks,
                }
            ),
            status_code,
        )

    except Exception as e:
        logger.exception(f"Error in detailed health check: {e}")
        return (
            jsonify(
                {
                    "status": "fail",
                    "version": "1.0",
                    "serviceId": "silvertrade",
                    "description": str(e),
                }
            ),
            503,
        )


# ============================================================================
# Dashboard - Served by React (see frontend/src/pages/HealthMonitor.tsx)
# Route: /health (handled by React Router in App.tsx)
# ============================================================================

# Note: The dashboard UI is now a React component at /health
# All data is fetched via API endpoints below

# ============================================================================
# API Endpoints (Authenticated)
# ============================================================================


@health_bp.route("/api/databases", methods=["GET"])
@check_session_validity
@limiter.limit("30/minute")
def get_database_health():
    """
    Ping all 5 databases and return per-database connectivity + pool stats.

    Tests every configured database connection by executing ``SELECT 1``
    and reports latency for each.  Also returns connection pool utilisation
    metrics (pool size, checked-in/out connections, in-use percentage).

    Response::

        {
          "status": "pass" | "degraded" | "fail",
          "databases": {
            "silvertrade": {"status": "pass", "latency_ms": 0.3, "driver": "sqlite"},
            "logs":        {"status": "pass", "latency_ms": 0.2, "driver": "sqlite"},
            "latency":     {"status": "pass", "latency_ms": 0.2, "driver": "sqlite"},
            "health":      {"status": "pass", "latency_ms": 0.3, "driver": "sqlite"},
            "sandbox":     {"status": "pass", "latency_ms": 0.2, "driver": "sqlite"},
          },
          "pool_stats": { ... },
        }

    - ``latency_ms`` is the round-trip time in milliseconds.
    - ``driver`` is the SQLAlchemy dialect name (e.g. ``sqlite``, ``postgresql``).
    - ``pool_stats`` includes connection pool utilisation metrics (QueuePool only).
    - For SQLite (NullPool), pool stats show ``"note": "No pool metrics for NullPool"``.
    """
    try:
        from database.db_config import check_all_databases

        result = check_all_databases()

        status_code = 200
        if result["status"] == "fail":
            status_code = 503
        elif result["status"] == "degraded":
            status_code = 200  # Still partial — report as OK with degradation info

        return jsonify(result), status_code
    except Exception as e:
        logger.exception(f"Error in database health check: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@health_bp.route("/api/bulkheads", methods=["GET"])
@check_session_validity
@limiter.limit("30/minute")
def get_bulkheads():
    """
    Return the state of all bulkhead thread pools and dead-letter queue.

    Bulkheads isolate different operation categories (orders, market data,
    database queries, admin) into separate thread pools so that a slow
    or failing subsystem cannot exhaust all application threads.

    Response::

        {
          "pools": {
            "orders": {
              "active": 2,
              "completed": 150,
              "rejected": 0,
              "max_workers": 5,
              "queue_size": 100,
              "queue_used": 3
            },
            "market_data": { ... },
            ...
          },
          "dead_letter_queue": [
            {
              "category": "orders",
              "task_name": "place_order",
              "error": "Connection refused",
              "submitted_at": 1234567890.0
            }
          ],
          "summaries": {
            "total_rejected": 0,
            "dead_letter_count": 0
          }
        }
    """
    try:
        from utils.bulkhead import (
            BulkheadCategory,
            DEFAULT_POOL_SIZES,
            QUEUE_SIZE,
            get_bulkhead_metrics,
            peek_dead_letter_queue,
        )

        metrics = get_bulkhead_metrics()
        dead_letters = peek_dead_letter_queue()

        pools = {}
        total_rejected = 0
        for cat in BulkheadCategory:
            active = metrics.get(f"{cat.value}_active", 0)
            completed = metrics.get(f"{cat.value}_completed", 0)
            rejected = metrics.get(f"{cat.value}_rejected", 0)
            total_rejected += rejected

            pools[cat.value] = {
                "active": active,
                "completed": completed,
                "rejected": rejected,
                "max_workers": DEFAULT_POOL_SIZES.get(cat, 3),
                "queue_size": QUEUE_SIZE,
                "queue_used": active,  # Active tasks sit in the queue while waiting for a worker
            }

        return jsonify({
            "pools": pools,
            "dead_letter_queue": [
                {
                    "category": entry.category.value,
                    "task_name": entry.task_name,
                    "error": entry.error,
                    "submitted_at": entry.submitted_at,
                }
                for entry in dead_letters
            ],
            "summaries": {
                "total_rejected": total_rejected,
                "dead_letter_count": len(dead_letters),
            },
        })
    except Exception as e:
        logger.exception(f"Error fetching bulkhead stats: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@health_bp.route("/api/brokers", methods=["GET"])
@check_session_validity
@limiter.limit("30/minute")
def get_broker_health():
    """
    Return per-user broker health states from the failover manager.

    Shows all registered users, their failover order, currently active
    broker, and per-broker health metrics (consecutive failures, last
    success/failure timestamps, healthy status).

    Response::

        {
          "enabled": true,
          "users": {
            "user123": {
              "active_broker": "zerodha",
              "failover_order": ["zerodha", "angel"],
              "brokers": {
                "zerodha": {
                  "consecutive_failures": 0,
                  "is_healthy": true,
                  "last_success_at": 1234567890.0,
                  "last_failure_at": 0.0
                },
                "angel": { ... }
              }
            }
          },
          "summary": {
            "total_users": 1,
            "total_brokers": 2,
            "healthy_brokers": 2,
            "unhealthy_brokers": 0
          }
        }
    """
    try:
        from utils.broker_failover import get_failover_manager

        fm = get_failover_manager()
        users = fm.get_all_broker_health()

        # Compute summary
        total_brokers = 0
        healthy_brokers = 0
        for user_id, user_data in users.items():
            for broker_name, health in user_data.get("brokers", {}).items():
                total_brokers += 1
                if health.get("is_healthy", True):
                    healthy_brokers += 1

        return jsonify({
            "enabled": fm._enabled,
            "users": users,
            "summary": {
                "total_users": len(users),
                "total_brokers": total_brokers,
                "healthy_brokers": healthy_brokers,
                "unhealthy_brokers": total_brokers - healthy_brokers,
            },
        })
    except Exception as e:
        logger.exception(f"Error fetching broker health: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@health_bp.route("/api/circuit-breakers", methods=["GET"])
@check_session_validity
@limiter.limit("30/minute")
def get_circuit_breakers():
    """
    Return the state of all registered circuit breakers.

    Circuit breakers protect broker API calls from cascading failures.
    When a broker is unhealthy, its circuit trips OPEN and subsequent
    requests fail fast instead of blocking request handler threads.

    Response::

        {
          "breakers": {
            "zerodha": {
              "name": "zerodha",
              "state": "CLOSED",
              "failure_count": 0,
              "success_count": 0,
              "failure_threshold": 5,
              "recovery_timeout": 30.0,
              "half_open_max_attempts": 3,
              "last_failure_time": 0.0,
              "total_failures": 0,
              "total_successes": 0
            },
            "angel": { ... },
            ...
          },
          "summary": {
            "total": 12,
            "closed": 10,
            "open": 1,
            "half_open": 1
          }
        }
    """
    try:
        from utils.circuit_breaker import get_all_breaker_stats

        stats = get_all_breaker_stats()

        closed = sum(1 for s in stats.values() if s["state"] == "CLOSED")
        open_ = sum(1 for s in stats.values() if s["state"] == "OPEN")
        half_open = sum(1 for s in stats.values() if s["state"] == "HALF_OPEN")

        return jsonify({
            "breakers": stats,
            "summary": {
                "total": len(stats),
                "closed": closed,
                "open": open_,
                "half_open": half_open,
            },
        })
    except Exception as e:
        logger.exception(f"Error fetching circuit breaker stats: {e}")
        return jsonify({"status": "error", "message": str(e)}), 500


@health_bp.route("/api/current", methods=["GET"])
@check_session_validity
@limiter.limit("60/minute")
def get_current_metrics():
    """Get current metrics snapshot"""
    try:
        metric = HealthMetric.get_current_metrics()
        if not metric:
            return jsonify({"error": "No metrics available"}), 404

        return jsonify(
            {
                "timestamp": convert_to_ist(metric.timestamp).isoformat(),
                "fd": {
                    "count": metric.fd_count or 0,
                    "limit": metric.fd_limit,
                    "usage_percent": metric.fd_usage_percent if metric.fd_usage_percent is not None else 0.0,
                    "status": metric.fd_status or "unknown",
                },
                "memory": {
                    "rss_mb": metric.memory_rss_mb,
                    "vms_mb": metric.memory_vms_mb,
                    "percent": metric.memory_percent,
                    "available_mb": metric.memory_available_mb,
                    "swap_mb": metric.memory_swap_mb,
                    "status": metric.memory_status,
                },
                "database": {
                    "total": metric.db_connections_total,
                    "connections": metric.db_connections,
                    "status": metric.db_status,
                },
                "websocket": {
                    "total": metric.ws_connections_total,
                    "connections": metric.ws_connections,
                    "total_symbols": metric.ws_total_symbols,
                    "status": metric.ws_status,
                },
                "threads": {
                    "count": metric.thread_count,
                    "stuck": metric.stuck_threads,
                    "status": metric.thread_status,
                    "details": metric.thread_details,
                },
                "processes": metric.process_details or [],
                "overall_status": metric.overall_status,
            }
        )
    except Exception as e:
        logger.exception(f"Error fetching current metrics: {e}")
        return jsonify({"error": str(e)}), 500


@health_bp.route("/api/history", methods=["GET"])
@check_session_validity
@limiter.limit("60/minute")
def get_metrics_history():
    """Get metrics history"""
    try:
        hours = min(max(int(request.args.get("hours", 24)), 1), 168)  # Range [1, 168]
        metrics = HealthMetric.get_metrics_history(hours=hours)

        return jsonify(
            [
                {
                    "timestamp": convert_to_ist(m.timestamp).isoformat(),
                    "fd_count": m.fd_count,
                    "memory_rss_mb": m.memory_rss_mb,
                    "db_connections": m.db_connections_total,
                    "ws_connections": m.ws_connections_total,
                    "threads": m.thread_count,
                    "overall_status": m.overall_status,
                }
                for m in metrics
            ]
        )
    except Exception as e:
        logger.exception(f"Error fetching metrics history: {e}")
        return jsonify({"error": str(e)}), 500


@health_bp.route("/api/stats", methods=["GET"])
@check_session_validity
@limiter.limit("60/minute")
def get_health_stats():
    """Get aggregated statistics"""
    try:
        hours = min(max(int(request.args.get("hours", 24)), 1), 168)  # Range [1, 168]
        stats = HealthMetric.get_stats(hours=hours)
        return jsonify(stats)
    except Exception as e:
        logger.exception(f"Error fetching stats: {e}")
        return jsonify({"error": str(e)}), 500


@health_bp.route("/api/alerts", methods=["GET"])
@check_session_validity
@limiter.limit("60/minute")
def get_alerts():
    """Get active alerts"""
    try:
        alerts = HealthAlert.get_active_alerts()
        return jsonify(
            [
                {
                    "id": alert.id,
                    "timestamp": convert_to_ist(alert.timestamp).isoformat(),
                    "alert_type": alert.alert_type,
                    "severity": alert.severity,
                    "metric_name": alert.metric_name,
                    "metric_value": alert.metric_value,
                    "threshold_value": alert.threshold_value,
                    "message": alert.message,
                    "acknowledged": alert.acknowledged,
                    "resolved": alert.resolved,
                }
                for alert in alerts
            ]
        )
    except Exception as e:
        logger.exception(f"Error fetching alerts: {e}")
        return jsonify({"error": str(e)}), 500


@health_bp.route("/api/alerts/<int:alert_id>/acknowledge", methods=["POST"])
@check_session_validity
@limiter.limit("30/minute")
def acknowledge_alert(alert_id):
    """Acknowledge an alert"""
    try:
        success = HealthAlert.acknowledge_alert(alert_id)
        if success:
            return jsonify({"status": "success", "message": "Alert acknowledged"})
        return jsonify({"status": "error", "message": "Alert not found"}), 404
    except Exception as e:
        logger.exception(f"Error acknowledging alert: {e}")
        return jsonify({"error": str(e)}), 500


@health_bp.route("/api/alerts/<int:alert_id>/resolve", methods=["POST"])
@check_session_validity
@limiter.limit("30/minute")
def resolve_alert(alert_id):
    """Resolve an alert"""
    try:
        success = HealthAlert.resolve_alert(alert_id)
        if success:
            return jsonify({"status": "success", "message": "Alert resolved"})
        return jsonify({"status": "error", "message": "Alert not found"}), 404
    except Exception as e:
        logger.exception(f"Error resolving alert: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Export
# ============================================================================


@health_bp.route("/export", methods=["GET"])
@check_session_validity
@limiter.limit("10/minute")
def export_metrics():
    """Export metrics to CSV"""
    try:
        hours = min(max(int(request.args.get("hours", 24)), 1), 168)  # Range [1, 168]
        metrics = HealthMetric.get_metrics_history(hours=hours)

        # Generate CSV
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        writer.writerow(
            [
                "Date & Time (IST)",
                "FD Count",
                "FD Limit",
                "FD Status",
                "Memory (MB)",
                "Memory Status",
                "DB Connections",
                "DB Status",
                "WebSocket Connections",
                "WS Status",
                "Threads",
                "Thread Status",
                "Overall Status",
            ]
        )

        # Write data
        for metric in metrics:
            writer.writerow(
                [
                    format_ist_time(metric.timestamp),
                    metric.fd_count or 0,
                    metric.fd_limit or 0,
                    metric.fd_status or "unknown",
                    round(metric.memory_rss_mb, 2) if metric.memory_rss_mb else 0,
                    metric.memory_status or "unknown",
                    metric.db_connections_total or 0,
                    metric.db_status or "unknown",
                    metric.ws_connections_total or 0,
                    metric.ws_status or "unknown",
                    metric.thread_count or 0,
                    metric.thread_status or "unknown",
                    metric.overall_status or "unknown",
                ]
            )

        csv_data = output.getvalue()

        # Create response
        response = Response(
            csv_data,
            mimetype="text/csv",
            headers={"Content-Disposition": "attachment; filename=health_metrics.csv"},
        )

        return response

    except Exception as e:
        logger.exception(f"Error exporting metrics: {e}")
        return jsonify({"error": str(e)}), 500


# ============================================================================
# Teardown
# ============================================================================


@health_bp.teardown_app_request
def shutdown_session(exception=None):
    """Remove scoped session after request"""
    health_session.remove()
