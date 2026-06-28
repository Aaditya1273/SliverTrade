"""Initial baseline migration for the Main database (public schema).

Creates all tables for:
  - Authentication & users (auth, api_keys, active_sessions, login_attempts, users)
  - Settings, strategies, symbols, workflows, Telegram, calendar, etc.

Generated from model definitions. This is the baseline revision — future
migrations will diff against this state.

Revision ID: 0001
Revises: None
Create Date: 2026-06-05
"""

import os
import sys

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect


# revision identifiers, used by Alembic.
revision = "0001"
down_revision = None
branch_labels = ("main_db",)
depends_on = None


def upgrade() -> None:
    """Create all Main database tables."""
    # ── auth_db tables ───────────────────────────────────────────
    op.create_table(
        "auth",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("auth", sa.Text(), nullable=False),
        sa.Column("feed_token", sa.Text(), nullable=True),
        sa.Column("broker", sa.String(20), nullable=False),
        sa.Column("user_id", sa.String(255), nullable=True),
        sa.Column("is_revoked", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("secret_api_key", sa.Text(), nullable=True),
        sa.Column("primary_ip", sa.String(45), nullable=True),
        sa.Column("secondary_ip", sa.String(45), nullable=True),
        sa.Column("ip_updated_at", sa.DateTime(), nullable=True),
        sa.Column("aux_param1", sa.Text(), nullable=True),
        sa.Column("aux_param2", sa.Text(), nullable=True),
        sa.Column("aux_param3", sa.Text(), nullable=True),
        sa.Column("aux_param4", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("idx_auth_broker", "auth", ["broker"])
    op.create_index("idx_auth_user_id", "auth", ["user_id"])
    op.create_index("idx_auth_is_revoked", "auth", ["is_revoked"])

    op.create_table(
        "api_keys",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(), nullable=False),
        sa.Column("api_key_hash", sa.Text(), nullable=False),
        sa.Column("api_key_encrypted", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("order_mode", sa.String(20), nullable=True, server_default=sa.text("'auto'")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index("idx_api_keys_order_mode", "api_keys", ["order_mode"])
    op.create_index("idx_api_keys_created_at", "api_keys", ["created_at"])

    op.create_table(
        "active_sessions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("session_id", sa.String(64), nullable=False),
        sa.Column("device_info", sa.String(500), nullable=True),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("broker", sa.String(20), nullable=True),
        sa.Column("login_time", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("last_seen", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("session_id"),
    )
    op.create_index("idx_active_sessions_username", "active_sessions", ["username"])

    op.create_table(
        "login_attempts",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(255), nullable=False),
        sa.Column("ip_address", sa.String(45), nullable=True),
        sa.Column("device_info", sa.String(500), nullable=True),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("login_type", sa.String(20), nullable=True),
        sa.Column("broker", sa.String(20), nullable=True),
        sa.Column("failure_reason", sa.String(255), nullable=True),
        sa.Column("timestamp", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_login_attempts_username", "login_attempts", ["username"])
    op.create_index("idx_login_attempts_timestamp", "login_attempts", ["timestamp"])
    op.create_index("idx_login_attempts_status", "login_attempts", ["status"])

    # ── user_db tables ───────────────────────────────────────────
    op.create_table(
        "users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("username", sa.String(80), nullable=False),
        sa.Column("email", sa.String(120), nullable=False),
        sa.Column("password_hash", sa.String(255), nullable=False),
        sa.Column("totp_secret", sa.String(255), nullable=False),
        sa.Column("is_admin", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("username"),
        sa.UniqueConstraint("email"),
    )

    # ── settings_db tables ───────────────────────────────────────
    op.create_table(
        "settings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("analyze_mode", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("smtp_server", sa.String(255), nullable=True),
        sa.Column("smtp_port", sa.Integer(), nullable=True),
        sa.Column("smtp_username", sa.String(255), nullable=True),
        sa.Column("smtp_password_encrypted", sa.Text(), nullable=True),
        sa.Column("smtp_use_tls", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("smtp_from_email", sa.String(255), nullable=True),
        sa.Column("smtp_helo_hostname", sa.String(255), nullable=True),
        sa.Column(
            "security_auto_ban_enabled",
            sa.Boolean(),
            nullable=True,
            server_default=sa.text("false"),
        ),
        sa.Column(
            "security_404_threshold", sa.Integer(), nullable=True, server_default=sa.text("100")
        ),
        sa.Column(
            "security_404_ban_duration", sa.Integer(), nullable=True, server_default=sa.text("0")
        ),
        sa.Column(
            "security_api_threshold", sa.Integer(), nullable=True, server_default=sa.text("100")
        ),
        sa.Column(
            "security_api_ban_duration", sa.Integer(), nullable=True, server_default=sa.text("0")
        ),
        sa.Column(
            "security_repeat_offender_limit",
            sa.Integer(),
            nullable=True,
            server_default=sa.text("2"),
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── symtoken (master contract) ────────────────────────────────
    op.create_table(
        "symtoken",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(), nullable=False),
        sa.Column("brsymbol", sa.String(), nullable=False),
        sa.Column("name", sa.String(), nullable=True),
        sa.Column("exchange", sa.String(), nullable=True),
        sa.Column("brexchange", sa.String(), nullable=True),
        sa.Column("token", sa.String(), nullable=True),
        sa.Column("expiry", sa.String(), nullable=True),
        sa.Column("strike", sa.Float(), nullable=True),
        sa.Column("lotsize", sa.Integer(), nullable=True),
        sa.Column("instrumenttype", sa.String(), nullable=True),
        sa.Column("tick_size", sa.Float(), nullable=True),
        sa.Column("contract_value", sa.Float(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("idx_symbol_exchange", "symtoken", ["symbol", "exchange"])
    op.create_index("idx_symbol_name", "symtoken", ["symbol", "name"])
    op.create_index("idx_brsymbol_exchange", "symtoken", ["brsymbol", "exchange"])
    op.create_index("ix_symtoken_brsymbol", "symtoken", ["brsymbol"])
    op.create_index("ix_symtoken_exchange", "symtoken", ["exchange"])
    op.create_index("ix_symtoken_symbol", "symtoken", ["symbol"])
    op.create_index("ix_symtoken_token", "symtoken", ["token"])

    # ── flow_db tables ───────────────────────────────────────────
    op.create_table(
        "flow_workflows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("nodes", sa.JSON(), nullable=True, server_default=sa.text("'[]'::json")),
        sa.Column("edges", sa.JSON(), nullable=True, server_default=sa.text("'[]'::json")),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("schedule_job_id", sa.String(255), nullable=True),
        sa.Column("webhook_token", sa.String(64), nullable=True),
        sa.Column("webhook_secret", sa.String(64), nullable=True),
        sa.Column("webhook_enabled", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column(
            "webhook_auth_type", sa.String(20), nullable=True, server_default=sa.text("'payload'")
        ),
        sa.Column("api_key", sa.String(255), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("webhook_token"),
    )
    op.create_index("ix_flow_workflows_id", "flow_workflows", ["id"])

    op.create_table(
        "flow_workflow_executions",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("workflow_id", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(50), nullable=True, server_default=sa.text("'pending'")),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("completed_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("logs", sa.JSON(), nullable=True, server_default=sa.text("'[]'::json")),
        sa.Column("error", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(["workflow_id"], ["flow_workflows.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_flow_workflow_executions_id", "flow_workflow_executions", ["id"])

    # ── telegram_db tables ───────────────────────────────────────
    op.create_table(
        "telegram_users",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.Integer(), nullable=False),
        sa.Column("silvertrade_username", sa.String(255), nullable=False),
        sa.Column("encrypted_api_key", sa.Text(), nullable=True),
        sa.Column("host_url", sa.String(500), nullable=True),
        sa.Column("first_name", sa.String(255), nullable=True),
        sa.Column("last_name", sa.String(255), nullable=True),
        sa.Column("telegram_username", sa.String(255), nullable=True),
        sa.Column("broker", sa.String(50), nullable=True, server_default=sa.text("'default'")),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column(
            "notifications_enabled", sa.Boolean(), nullable=True, server_default=sa.text("true")
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("last_command_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("telegram_id"),
    )
    op.create_index("ix_telegram_users_telegram_id", "telegram_users", ["telegram_id"])
    op.create_index(
        "ix_telegram_users_silvertrade_username", "telegram_users", ["silvertrade_username"]
    )

    op.create_table(
        "bot_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("token", sa.Text(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("bot_username", sa.String(255), nullable=True),
        sa.Column(
            "max_message_length", sa.Integer(), nullable=True, server_default=sa.text("4096")
        ),
        sa.Column(
            "rate_limit_per_minute", sa.Integer(), nullable=True, server_default=sa.text("30")
        ),
        sa.Column("broadcast_enabled", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "command_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.Integer(), nullable=False),
        sa.Column("command", sa.String(100), nullable=False),
        sa.Column("chat_id", sa.Integer(), nullable=True),
        sa.Column("parameters", sa.Text(), nullable=True),
        sa.Column("executed_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["telegram_id"],
            ["telegram_users.telegram_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_command_logs_telegram_id", "command_logs", ["telegram_id"])

    op.create_table(
        "notification_queue",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("telegram_id", sa.Integer(), nullable=False),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=True, server_default=sa.text("5")),
        sa.Column("status", sa.String(20), nullable=True, server_default=sa.text("'pending'")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("sent_at", sa.DateTime(), nullable=True),
        sa.Column("error_message", sa.Text(), nullable=True),
        sa.ForeignKeyConstraint(
            ["telegram_id"],
            ["telegram_users.telegram_id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_notification_queue_status", "notification_queue", ["status"])

    op.create_table(
        "user_preferences",
        sa.Column("telegram_id", sa.Integer(), nullable=False),
        sa.Column(
            "order_notifications", sa.Boolean(), nullable=True, server_default=sa.text("true")
        ),
        sa.Column(
            "trade_notifications", sa.Boolean(), nullable=True, server_default=sa.text("true")
        ),
        sa.Column("pnl_notifications", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("daily_summary", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("summary_time", sa.String(10), nullable=True, server_default=sa.text("'18:00'")),
        sa.Column("language", sa.String(10), nullable=True, server_default=sa.text("'en'")),
        sa.Column(
            "timezone", sa.String(50), nullable=True, server_default=sa.text("'Asia/Kolkata'")
        ),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.ForeignKeyConstraint(
            ["telegram_id"],
            ["telegram_users.telegram_id"],
        ),
        sa.PrimaryKeyConstraint("telegram_id"),
    )

    # ── master_contract_status ──────────────────────────────────
    op.create_table(
        "master_contract_status",
        sa.Column("broker", sa.String(), nullable=False),
        sa.Column("status", sa.String(), nullable=True, server_default=sa.text("'pending'")),
        sa.Column("message", sa.String(), nullable=True),
        sa.Column("last_updated", sa.DateTime(), nullable=True),
        sa.Column("total_symbols", sa.String(), nullable=True, server_default=sa.text("'0'")),
        sa.Column("is_ready", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("last_download_time", sa.DateTime(), nullable=True),
        sa.Column("download_date", sa.Date(), nullable=True),
        sa.Column("exchange_stats", sa.Text(), nullable=True),
        sa.Column("download_duration_seconds", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("broker"),
    )

    # ── strategies / chartink tables ─────────────────────────────
    op.create_table(
        "strategies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user", sa.String(100), nullable=False),
        sa.Column("strategy_name", sa.String(100), nullable=False),
        sa.Column("webhook_token", sa.String(100), nullable=True),
        sa.Column("isinactive", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("is_intraday", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("last_triggered_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "chartink_strategies",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user", sa.String(100), nullable=False),
        sa.Column("strategy_name", sa.String(100), nullable=False),
        sa.Column("webhook_token", sa.String(100), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("is_intraday", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("last_triggered_at", sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── organization_db ─────────────────────────────────────────
    op.create_table(
        "organizations",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(255), nullable=False),
        sa.Column("domain", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("domain"),
    )

    op.create_table(
        "organization_roles",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("organization_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("permissions", sa.JSON(), nullable=True),
        sa.Column("is_system_role", sa.Boolean(), nullable=True, server_default=sa.text("false")),
        sa.ForeignKeyConstraint(
            ["organization_id"],
            ["organizations.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )

    # ── market_calendar ──────────────────────────────────────────
    op.create_table(
        "holidays",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("date", sa.Date(), nullable=False),
        sa.Column("description", sa.String(255), nullable=True),
        sa.Column("is_open", sa.Boolean(), nullable=False, server_default=sa.text("false")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "market_timings",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("exchange", sa.String(20), nullable=False),
        sa.Column("start_offset", sa.BigInteger(), nullable=True),
        sa.Column("end_offset", sa.BigInteger(), nullable=True),
        sa.Column("description", sa.String(255), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("exchange"),
    )

    # ── Misc tables ──────────────────────────────────────────────
    op.create_table(
        "chart_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.String(100), nullable=False),
        sa.Column("preferences", sa.JSON(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "qty_freeze",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("symbol", sa.String(50), nullable=True),
        sa.Column("exchange", sa.String(20), nullable=True),
        sa.Column("freeze_qty", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "leverage_config",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("leverage", sa.Integer(), nullable=True, server_default=sa.text("1")),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "action_center_pending_orders",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user", sa.String(100), nullable=False),
        sa.Column("symbol", sa.String(50), nullable=False),
        sa.Column("exchange", sa.String(20), nullable=False),
        sa.Column("action", sa.String(10), nullable=False),
        sa.Column("quantity", sa.Integer(), nullable=False),
        sa.Column("price_type", sa.String(20), nullable=True),
        sa.Column("product", sa.String(20), nullable=True),
        sa.Column("price", sa.String(20), nullable=True),
        sa.Column("trigger_price", sa.String(20), nullable=True),
        sa.Column("disclosed_quantity", sa.Integer(), nullable=True),
        sa.Column("order_id", sa.String(50), nullable=True),
        sa.Column("status", sa.String(20), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("rejection_reason", sa.Text(), nullable=True),
        sa.Column("approved_at", sa.DateTime(), nullable=True),
        sa.Column("approved_by", sa.String(100), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "analyzer_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("api_key", sa.String(255), nullable=False),
        sa.Column("endpoint", sa.String(255), nullable=False),
        sa.Column("request_data", sa.Text(), nullable=True),
        sa.Column("response_data", sa.Text(), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "order_logs",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("api_key", sa.String(255), nullable=False),
        sa.Column("endpoint", sa.String(255), nullable=False),
        sa.Column("request_data", sa.Text(), nullable=True),
        sa.Column("response_data", sa.Text(), nullable=True),
        sa.Column("status_code", sa.Integer(), nullable=True),
        sa.Column("duration_ms", sa.Integer(), nullable=True),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "strategy_portfolio",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user", sa.String(100), nullable=False),
        sa.Column("name", sa.String(100), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("config", sa.JSON(), nullable=True),
        sa.Column("is_active", sa.Boolean(), nullable=True, server_default=sa.text("true")),
        sa.Column("created_at", sa.DateTime(), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.func.now()),
        sa.PrimaryKeyConstraint("id"),
    )


def downgrade() -> None:
    """Drop all Main database tables."""
    op.drop_table("strategy_portfolio")
    op.drop_table("order_logs")
    op.drop_table("analyzer_logs")
    op.drop_table("action_center_pending_orders")
    op.drop_table("leverage_config")
    op.drop_table("qty_freeze")
    op.drop_table("chart_preferences")
    op.drop_table("market_timings")
    op.drop_table("holidays")
    op.drop_table("organization_roles")
    op.drop_table("organizations")
    op.drop_table("chartink_strategies")
    op.drop_table("strategies")
    op.drop_table("master_contract_status")
    op.drop_table("user_preferences")
    op.drop_table("notification_queue")
    op.drop_table("command_logs")
    op.drop_table("bot_config")
    op.drop_table("telegram_users")
    op.drop_table("flow_workflow_executions")
    op.drop_table("flow_workflows")
    op.drop_table("symtoken")
    op.drop_table("settings")
    op.drop_table("users")
    op.drop_table("login_attempts")
    op.drop_table("active_sessions")
    op.drop_table("api_keys")
    op.drop_table("auth")
