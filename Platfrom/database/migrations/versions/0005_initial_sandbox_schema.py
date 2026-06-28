"""Initial baseline migration for the Sandbox database (sandbox schema).

Creates tables for paper trading sandbox:
  - sandbox_orders, sandbox_trades, sandbox_positions, sandbox_holdings
  - sandbox_funds, sandbox_daily_pnl, sandbox_config, sandbox_gtt, sandbox_gtt_legs

Revision ID: 0005
Revises: None
Create Date: 2026-06-05
"""

from alembic import op
import sqlalchemy as sa


revision = "0005"
down_revision = None
branch_labels = ("sandbox_db",)
depends_on = None


def upgrade() -> None:
    """Create all Sandbox database tables."""
    op.create_table(
        "sandbox_orders",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("orderid", sa.String(50), nullable=False, unique=True),
        sa.Column("user_id", sa.String(50), nullable=False),
        sa.Column("strategy", sa.String(100), nullable=True),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("exchange", sa.String(20), nullable=False),
        sa.Column("action", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price", sa.DECIMAL(10, 2), nullable=True),
        sa.Column("trigger_price", sa.DECIMAL(10, 2), nullable=True),
        sa.Column("price_type", sa.String(20), nullable=False),
        sa.Column("product", sa.String(20), nullable=False),
        sa.Column("order_status", sa.String(20), nullable=False, server_default=sa.text("'open'")),
        sa.Column("average_price", sa.DECIMAL(10, 2), nullable=True),
        sa.Column("filled_quantity", sa.Integer(), server_default=sa.text("0")),
        sa.Column("pending_quantity", sa.Integer(), nullable=False),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column(
            "margin_blocked", sa.DECIMAL(10, 2), nullable=True, server_default=sa.text("0.00")
        ),
        sa.Column("order_timestamp", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("update_timestamp", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        # Check constraints mirroring sandbox_db.py models
        sa.CheckConstraint(
            "order_status IN ('open', 'complete', 'cancelled', 'rejected')",
            name="check_order_status",
        ),
        sa.CheckConstraint("action IN ('BUY', 'SELL')", name="check_action"),
        sa.CheckConstraint(
            "price_type IN ('MARKET', 'LIMIT', 'SL', 'SL-M')", name="check_price_type"
        ),
        sa.CheckConstraint("product IN ('CNC', 'NRML', 'MIS')", name="check_product"),
    )
    op.create_index("ix_sandbox_orders_orderid", "sandbox_orders", ["orderid"])
    op.create_index("ix_sandbox_orders_user_id", "sandbox_orders", ["user_id"])
    op.create_index("ix_sandbox_orders_symbol", "sandbox_orders", ["symbol"])
    op.create_index("ix_sandbox_orders_exchange", "sandbox_orders", ["exchange"])
    op.create_index("ix_sandbox_orders_order_status", "sandbox_orders", ["order_status"])
    op.create_index("idx_user_status", "sandbox_orders", ["user_id", "order_status"])
    op.create_index("idx_symbol_exchange", "sandbox_orders", ["symbol", "exchange"])

    op.create_table(
        "sandbox_trades",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("tradeid", sa.String(50), nullable=False, unique=True),
        sa.Column("orderid", sa.String(50), nullable=False),
        sa.Column("user_id", sa.String(50), nullable=False),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("exchange", sa.String(20), nullable=False),
        sa.Column("action", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price", sa.DECIMAL(10, 2), nullable=False),
        sa.Column("product", sa.String(20), nullable=False),
        sa.Column("strategy", sa.String(100), nullable=True),
        sa.Column("trade_timestamp", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sandbox_trades_tradeid", "sandbox_trades", ["tradeid"])
    op.create_index("ix_sandbox_trades_orderid", "sandbox_trades", ["orderid"])
    op.create_index("ix_sandbox_trades_user_id", "sandbox_trades", ["user_id"])
    op.create_index("ix_sandbox_trades_symbol", "sandbox_trades", ["symbol"])
    op.create_index("ix_sandbox_trades_exchange", "sandbox_trades", ["exchange"])
    op.create_index("idx_user_symbol", "sandbox_trades", ["user_id", "symbol"])
    op.create_index("idx_orderid", "sandbox_trades", ["orderid"])

    op.create_table(
        "sandbox_positions",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(50), nullable=False),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("exchange", sa.String(20), nullable=False),
        sa.Column("product", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("average_price", sa.DECIMAL(10, 2), nullable=False),
        sa.Column("ltp", sa.DECIMAL(10, 2), nullable=True),
        sa.Column("pnl", sa.DECIMAL(10, 2), server_default=sa.text("0.00")),
        sa.Column("pnl_percent", sa.DECIMAL(10, 4), server_default=sa.text("0.00")),
        sa.Column("accumulated_realized_pnl", sa.DECIMAL(10, 2), server_default=sa.text("0.00")),
        sa.Column("today_realized_pnl", sa.DECIMAL(10, 2), server_default=sa.text("0.00")),
        sa.Column("margin_blocked", sa.DECIMAL(15, 2), server_default=sa.text("0.00")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "symbol", "exchange", "product", name="unique_position"),
    )
    op.create_index("ix_sandbox_positions_user_id", "sandbox_positions", ["user_id"])
    op.create_index("ix_sandbox_positions_symbol", "sandbox_positions", ["symbol"])
    op.create_index("ix_sandbox_positions_exchange", "sandbox_positions", ["exchange"])
    op.create_index("idx_user_product", "sandbox_positions", ["user_id", "product"])

    op.create_table(
        "sandbox_holdings",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(50), nullable=False),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("exchange", sa.String(20), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("average_price", sa.DECIMAL(10, 2), nullable=False),
        sa.Column("ltp", sa.DECIMAL(10, 2), nullable=True),
        sa.Column("pnl", sa.DECIMAL(10, 2), server_default=sa.text("0.00")),
        sa.Column("pnl_percent", sa.DECIMAL(10, 4), server_default=sa.text("0.00")),
        sa.Column("settlement_date", sa.Date(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "symbol", "exchange", name="unique_holding"),
    )
    op.create_index("ix_sandbox_holdings_user_id", "sandbox_holdings", ["user_id"])
    op.create_index("ix_sandbox_holdings_symbol", "sandbox_holdings", ["symbol"])
    op.create_index("ix_sandbox_holdings_exchange", "sandbox_holdings", ["exchange"])

    op.create_table(
        "sandbox_funds",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(50), nullable=False, unique=True),
        sa.Column("total_capital", sa.DECIMAL(15, 2), server_default=sa.text("10000000.00")),
        sa.Column("available_balance", sa.DECIMAL(15, 2), server_default=sa.text("10000000.00")),
        sa.Column("used_margin", sa.DECIMAL(15, 2), server_default=sa.text("0.00")),
        sa.Column("realized_pnl", sa.DECIMAL(15, 2), server_default=sa.text("0.00")),
        sa.Column("today_realized_pnl", sa.DECIMAL(15, 2), server_default=sa.text("0.00")),
        sa.Column("unrealized_pnl", sa.DECIMAL(15, 2), server_default=sa.text("0.00")),
        sa.Column("total_pnl", sa.DECIMAL(15, 2), server_default=sa.text("0.00")),
        sa.Column("last_reset_date", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("reset_count", sa.Integer(), server_default=sa.text("0")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sandbox_funds_user_id", "sandbox_funds", ["user_id"])

    op.create_table(
        "sandbox_daily_pnl",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("user_id", sa.String(50), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("realized_pnl", sa.DECIMAL(15, 2), server_default=sa.text("0.00")),
        sa.Column("positions_unrealized_pnl", sa.DECIMAL(15, 2), server_default=sa.text("0.00")),
        sa.Column("holdings_unrealized_pnl", sa.DECIMAL(15, 2), server_default=sa.text("0.00")),
        sa.Column("total_mtm", sa.DECIMAL(15, 2), server_default=sa.text("0.00")),
        sa.Column("available_balance", sa.DECIMAL(15, 2), server_default=sa.text("0.00")),
        sa.Column("used_margin", sa.DECIMAL(15, 2), server_default=sa.text("0.00")),
        sa.Column("portfolio_value", sa.DECIMAL(15, 2), server_default=sa.text("0.00")),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "date", name="unique_user_daily_pnl"),
    )
    op.create_index("ix_sandbox_daily_pnl_user_id", "sandbox_daily_pnl", ["user_id"])
    op.create_index("ix_sandbox_daily_pnl_date", "sandbox_daily_pnl", ["date"])
    op.create_index("idx_user_date", "sandbox_daily_pnl", ["user_id", "date"])

    op.create_table(
        "sandbox_config",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("config_key", sa.String(100), nullable=False, unique=True),
        sa.Column("config_value", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_sandbox_config_config_key", "sandbox_config", ["config_key"])

    op.create_table(
        "sandbox_gtt",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("gtt_id", sa.String(50), nullable=False, unique=True),
        sa.Column("user_id", sa.String(50), nullable=False),
        sa.Column("strategy", sa.String(100), nullable=True),
        sa.Column("trigger_type", sa.String(10), nullable=False),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("exchange", sa.String(20), nullable=False),
        sa.Column("last_price", sa.DECIMAL(10, 2), nullable=False),
        sa.Column("gtt_status", sa.String(20), nullable=False, server_default=sa.text("'active'")),
        sa.Column(
            "margin_blocked", sa.DECIMAL(15, 2), nullable=False, server_default=sa.text("0.00")
        ),
        sa.Column("expires_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        # Check constraints mirroring sandbox_db.py models
        sa.CheckConstraint("trigger_type IN ('single', 'two-leg')", name="check_gtt_trigger_type"),
        sa.CheckConstraint(
            "gtt_status IN ('active', 'triggered', 'cancelled', 'expired', 'rejected')",
            name="check_gtt_status",
        ),
    )
    op.create_index("ix_sandbox_gtt_gtt_id", "sandbox_gtt", ["gtt_id"])
    op.create_index("ix_sandbox_gtt_user_id", "sandbox_gtt", ["user_id"])
    op.create_index("ix_sandbox_gtt_symbol", "sandbox_gtt", ["symbol"])
    op.create_index("ix_sandbox_gtt_exchange", "sandbox_gtt", ["exchange"])
    op.create_index("idx_gtt_user_status", "sandbox_gtt", ["user_id", "gtt_status"])
    op.create_index("idx_gtt_symbol_exchange", "sandbox_gtt", ["symbol", "exchange"])

    op.create_table(
        "sandbox_gtt_legs",
        sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
        sa.Column("gtt_id", sa.String(50), nullable=False),
        sa.Column("leg_number", sa.Integer(), nullable=False),
        sa.Column("trigger_price", sa.DECIMAL(10, 2), nullable=False),
        sa.Column("action", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price", sa.DECIMAL(10, 2), nullable=False),
        sa.Column("pricetype", sa.String(10), nullable=False, server_default=sa.text("'LIMIT'")),
        sa.Column("product", sa.String(10), nullable=False),
        sa.Column("leg_status", sa.String(20), nullable=False, server_default=sa.text("'pending'")),
        sa.Column("triggered_order_id", sa.String(50), nullable=True),
        sa.Column("leg_margin", sa.DECIMAL(15, 2), nullable=False, server_default=sa.text("0.00")),
        sa.Column("claimed_at", sa.DateTime(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()),
        sa.ForeignKeyConstraint(["gtt_id"], ["sandbox_gtt.gtt_id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        # Check constraints mirroring sandbox_db.py models
        sa.CheckConstraint(
            "leg_status IN ('pending', 'triggering', 'triggered', 'cancelled')",
            name="check_gtt_leg_status",
        ),
        sa.CheckConstraint("action IN ('BUY', 'SELL')", name="check_gtt_leg_action"),
        sa.CheckConstraint("product IN ('CNC', 'NRML', 'MIS')", name="check_gtt_leg_product"),
    )
    op.create_index("ix_sandbox_gtt_legs_gtt_id", "sandbox_gtt_legs", ["gtt_id"])
    op.create_index("idx_gtt_leg_status_claimed", "sandbox_gtt_legs", ["leg_status", "claimed_at"])


def downgrade() -> None:
    """Drop all Sandbox database tables."""
    op.drop_table("sandbox_gtt_legs")
    op.drop_table("sandbox_gtt")
    op.drop_table("sandbox_config")
    op.drop_table("sandbox_daily_pnl")
    op.drop_table("sandbox_funds")
    op.drop_table("sandbox_holdings")
    op.drop_table("sandbox_positions")
    op.drop_table("sandbox_trades")
    op.drop_table("sandbox_orders")
