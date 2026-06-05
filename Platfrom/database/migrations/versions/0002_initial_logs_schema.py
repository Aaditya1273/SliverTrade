"""Initial baseline migration for the Logs database (logs schema).

Creates tables for traffic logging, IP bans, and security tracking:
  - traffic_logs, ip_bans, error_404_tracker, invalid_api_key_tracker

Revision ID: 0002
Revises: None
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa


revision = "0002"
down_revision = None
branch_labels = ("logs_db",)
depends_on = None


def upgrade() -> None:
    """Create all Logs database tables."""
    op.create_table(
        "traffic_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("client_ip", sa.String(50), nullable=False),
        sa.Column("method", sa.String(10), nullable=False),
        sa.Column("path", sa.String(500), nullable=False),
        sa.Column("status_code", sa.Integer(), nullable=False),
        sa.Column("duration_ms", sa.Float(), nullable=False),
        sa.Column("host", sa.String(500), nullable=True),
        sa.Column("error", sa.String(500), nullable=True),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_traffic_timestamp", "traffic_logs", ["timestamp"])
    op.create_index("idx_traffic_client_ip", "traffic_logs", ["client_ip"])
    op.create_index("idx_traffic_status_code", "traffic_logs", ["status_code"])
    op.create_index("idx_traffic_user_id", "traffic_logs", ["user_id"])
    op.create_index("idx_traffic_ip_timestamp", "traffic_logs", ["client_ip", "timestamp"])

    op.create_table(
        "ip_bans",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ip_address", sa.String(50), nullable=False),
        sa.Column("ban_reason", sa.String(200), nullable=True),
        sa.Column("ban_count", sa.Integer(), nullable=True, server_default=sa.text("1")),
        sa.Column("banned_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("expires_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("is_permanent", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("created_by", sa.String(50), nullable=True, server_default=sa.text("'system'")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("ip_address"),
    )
    op.create_index("ix_ip_bans_ip_address", "ip_bans", ["ip_address"])

    op.create_table(
        "error_404_tracker",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ip_address", sa.String(50), nullable=False),
        sa.Column("error_count", sa.Integer(), nullable=True, server_default=sa.text("1")),
        sa.Column("first_error_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_error_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("paths_attempted", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_404_error_count", "error_404_tracker", ["error_count"])
    op.create_index("idx_404_first_error_at", "error_404_tracker", ["first_error_at"])
    op.create_index("ix_error_404_tracker_ip_address", "error_404_tracker", ["ip_address"])

    op.create_table(
        "invalid_api_key_tracker",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("ip_address", sa.String(50), nullable=False),
        sa.Column("attempt_count", sa.Integer(), nullable=True, server_default=sa.text("1")),
        sa.Column("first_attempt_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_attempt_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("api_keys_tried", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_api_tracker_attempt_count", "invalid_api_key_tracker", ["attempt_count"])
    op.create_index("idx_api_tracker_first_attempt_at", "invalid_api_key_tracker", ["first_attempt_at"])
    op.create_index("ix_invalid_api_key_tracker_ip_address", "invalid_api_key_tracker", ["ip_address"])


def downgrade() -> None:
    """Drop all Logs database tables."""
    op.drop_table("invalid_api_key_tracker")
    op.drop_table("error_404_tracker")
    op.drop_table("ip_bans")
    op.drop_table("traffic_logs")
