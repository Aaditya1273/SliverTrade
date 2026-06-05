"""Initial baseline migration for the Latency database (latency schema).

Creates table for order execution latency tracking.

Revision ID: 0003
Revises: None
Create Date: 2026-06-05
"""
from alembic import op
import sqlalchemy as sa


revision = "0003"
down_revision = None
branch_labels = ("latency_db",)
depends_on = None


def upgrade() -> None:
    """Create all Latency database tables."""
    op.create_table(
        "order_latency",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("order_id", sa.String(100), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=True),
        sa.Column("broker", sa.String(50), nullable=True),
        sa.Column("symbol", sa.String(50), nullable=True),
        sa.Column("order_type", sa.String(20), nullable=True),
        sa.Column("rtt_ms", sa.Float(), nullable=True),
        sa.Column("validation_latency_ms", sa.Float(), nullable=True),
        sa.Column("response_latency_ms", sa.Float(), nullable=True),
        sa.Column("overhead_ms", sa.Float(), nullable=True),
        sa.Column("total_latency_ms", sa.Float(), nullable=False),
        sa.Column("request_body", sa.JSON(), nullable=True),
        sa.Column("response_body", sa.JSON(), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("error", sa.String(500), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop all Latency database tables."""
    op.drop_table("order_latency")
