"""Initial baseline migration for the Health database (health schema).

Creates tables for system health monitoring and alerting:
  - health_metrics, health_alerts

Revision ID: 0004
Revises: None
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa


revision = "0004"
down_revision = None
branch_labels = ("health_db",)
depends_on = None


def upgrade() -> None:
    """Create all Health database tables."""
    op.create_table(
        "health_metrics",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("fd_count", sa.Integer(), nullable=True),
        sa.Column("fd_limit", sa.Integer(), nullable=True),
        sa.Column("fd_usage_percent", sa.Float(), nullable=True),
        sa.Column("fd_available", sa.Integer(), nullable=True),
        sa.Column("fd_status", sa.String(20), nullable=True),
        sa.Column("memory_rss_mb", sa.Float(), nullable=True),
        sa.Column("memory_vms_mb", sa.Float(), nullable=True),
        sa.Column("memory_percent", sa.Float(), nullable=True),
        sa.Column("memory_available_mb", sa.Float(), nullable=True),
        sa.Column("memory_swap_mb", sa.Float(), nullable=True),
        sa.Column("memory_status", sa.String(20), nullable=True),
        sa.Column("db_connections_total", sa.Integer(), nullable=True),
        sa.Column("db_connections", sa.JSON(), nullable=True),
        sa.Column("db_status", sa.String(20), nullable=True),
        sa.Column("ws_connections_total", sa.Integer(), nullable=True),
        sa.Column("ws_connections", sa.JSON(), nullable=True),
        sa.Column("ws_total_symbols", sa.Integer(), nullable=True),
        sa.Column("ws_status", sa.String(20), nullable=True),
        sa.Column("thread_count", sa.Integer(), nullable=True),
        sa.Column("stuck_threads", sa.Integer(), nullable=True),
        sa.Column("thread_details", sa.JSON(), nullable=True),
        sa.Column("thread_status", sa.String(20), nullable=True),
        sa.Column("process_details", sa.JSON(), nullable=True),
        sa.Column("overall_status", sa.String(20), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "health_alerts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("alert_type", sa.String(50), nullable=True),
        sa.Column("severity", sa.String(20), nullable=True),
        sa.Column("metric_name", sa.String(50), nullable=True),
        sa.Column("metric_value", sa.Float(), nullable=True),
        sa.Column("threshold_value", sa.Float(), nullable=True),
        sa.Column("message", sa.String(500), nullable=True),
        sa.Column("acknowledged", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("acknowledged_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("resolved", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("resolved_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop all Health database tables."""
    op.drop_table("health_alerts")
    op.drop_table("health_metrics")
