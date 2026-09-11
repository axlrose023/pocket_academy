"""Create Pocket Academy schema.

Revision ID: 56ec05931fe8
Revises:
Create Date: 2025-12-01 11:16:50.928805
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision: str = "56ec05931fe8"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def _id_column() -> sa.Column:
    return sa.Column(
        "id",
        sa.UUID(),
        primary_key=True,
        server_default=sa.text("gen_random_uuid()"),
        nullable=False,
    )


def _timestamps() -> tuple[sa.Column, sa.Column]:
    return (
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("CURRENT_TIMESTAMP"),
            nullable=False,
        ),
    )


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS pgcrypto")
    op.create_table(
        "users",
        _id_column(),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("username", sa.String(length=64)),
        sa.Column("first_name", sa.String(length=255)),
        sa.Column("last_name", sa.String(length=255)),
        sa.Column("language_code", sa.String(length=16)),
        sa.Column("last_seen_at", sa.DateTime(timezone=True)),
        sa.Column(
            "is_admin", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "is_manually_blocked",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
        sa.Column("manual_block_reason", sa.String(length=500)),
        *_timestamps(),
        sa.UniqueConstraint("telegram_id", name=op.f("users_telegram_id_key")),
    )
    op.create_index(op.f("users_username_idx"), "users", ["username"])
    op.create_index(op.f("users_last_seen_at_idx"), "users", ["last_seen_at"])

    op.create_table(
        "attribution_clicks",
        _id_column(),
        sa.Column("telegram_id", sa.BigInteger(), nullable=False),
        sa.Column("click_id", sa.String(length=255), nullable=False),
        sa.Column("link_chat", sa.Text()),
        sa.Column("source_created_at", sa.DateTime(timezone=True)),
        sa.Column("recorded_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.UniqueConstraint("click_id", name=op.f("attribution_clicks_click_id_key")),
    )
    op.create_index(
        op.f("attribution_clicks_telegram_id_idx"),
        "attribution_clicks",
        ["telegram_id"],
    )
    op.create_index(
        "attribution_clicks_telegram_recorded_idx",
        "attribution_clicks",
        ["telegram_id", "recorded_at"],
    )

    op.create_table(
        "external_events",
        _id_column(),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("event_type", sa.String(length=32), nullable=False),
        sa.Column("deduplication_key", sa.String(length=128), nullable=False),
        sa.Column("source_event_id", sa.String(length=255)),
        sa.Column("processing_status", sa.String(length=16), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True)),
        sa.Column("received_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("processed_at", sa.DateTime(timezone=True)),
        sa.Column("rejection_reason", sa.Text()),
        *_timestamps(),
        sa.UniqueConstraint(
            "deduplication_key",
            name=op.f("external_events_deduplication_key_key"),
        ),
    )
    op.create_index(
        op.f("external_events_source_event_id_idx"),
        "external_events",
        ["source_event_id"],
    )
    op.create_index(
        op.f("external_events_processing_status_idx"),
        "external_events",
        ["processing_status"],
    )
    op.create_index(
        "external_events_provider_type_occurred_idx",
        "external_events",
        ["provider", "event_type", "occurred_at"],
    )

    op.create_table(
        "broker_accounts",
        _id_column(),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("attribution_click_id", sa.UUID()),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("trader_id", sa.String(length=255), nullable=False),
        sa.Column("registered_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["attribution_click_id"],
            ["attribution_clicks.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(op.f("broker_accounts_user_id_idx"), "broker_accounts", ["user_id"])
    op.create_index(
        "broker_accounts_provider_trader_key",
        "broker_accounts",
        ["provider", "trader_id"],
        unique=True,
    )

    op.create_table(
        "deposits",
        _id_column(),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("broker_account_id", sa.UUID(), nullable=False),
        sa.Column("external_event_id", sa.UUID(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.CheckConstraint("amount > 0", name=op.f("deposits_amount_positive_check")),
        sa.CheckConstraint(
            "kind IN ('first', 'repeat')",
            name=op.f("deposits_kind_known_check"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["broker_account_id"],
            ["broker_accounts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["external_event_id"],
            ["external_events.id"],
            ondelete="RESTRICT",
        ),
        sa.UniqueConstraint(
            "external_event_id", name=op.f("deposits_external_event_id_key")
        ),
    )
    op.create_index(op.f("deposits_user_id_idx"), "deposits", ["user_id"])
    op.create_index(
        op.f("deposits_broker_account_id_idx"), "deposits", ["broker_account_id"]
    )
    op.create_index(
        "deposits_user_occurred_idx", "deposits", ["user_id", "occurred_at"]
    )

    op.create_table(
        "withdrawals",
        _id_column(),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("broker_account_id", sa.UUID(), nullable=False),
        sa.Column("last_external_event_id", sa.UUID()),
        sa.Column("provider", sa.String(length=32), nullable=False),
        sa.Column("external_reference", sa.String(length=255), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("resolved_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.CheckConstraint(
            "amount > 0", name=op.f("withdrawals_amount_positive_check")
        ),
        sa.CheckConstraint(
            "status IN ('new', 'cancelled', 'success')",
            name=op.f("withdrawals_status_known_check"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["broker_account_id"],
            ["broker_accounts.id"],
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["last_external_event_id"],
            ["external_events.id"],
            ondelete="SET NULL",
        ),
    )
    op.create_index(op.f("withdrawals_user_id_idx"), "withdrawals", ["user_id"])
    op.create_index(
        op.f("withdrawals_broker_account_id_idx"), "withdrawals", ["broker_account_id"]
    )
    op.create_index(
        "withdrawals_user_status_requested_idx",
        "withdrawals",
        ["user_id", "status", "requested_at"],
    )
    op.create_index(
        "withdrawals_provider_reference_key",
        "withdrawals",
        ["provider", "external_reference"],
        unique=True,
    )

    op.create_table(
        "pac_ledger_entries",
        _id_column(),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("amount", sa.Numeric(precision=14, scale=2), nullable=False),
        sa.Column("reason", sa.String(length=32), nullable=False),
        sa.Column("reference_day", sa.Date()),
        sa.Column("reference_id", sa.UUID()),
        sa.Column("note", sa.String(length=500)),
        *_timestamps(),
        sa.CheckConstraint(
            "amount <> 0", name=op.f("pac_ledger_entries_amount_nonzero_check")
        ),
        sa.CheckConstraint(
            "reason IN ('deposit', 'product_purchase', 'diary_streak_reward', 'manual_adjustment')",
            name=op.f("pac_ledger_entries_reason_known_check"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(
        op.f("pac_ledger_entries_user_id_idx"), "pac_ledger_entries", ["user_id"]
    )
    op.create_index(
        "pac_ledger_entries_user_created_idx",
        "pac_ledger_entries",
        ["user_id", "created_at"],
    )
    op.create_index(
        "pac_ledger_entries_user_reason_day_key",
        "pac_ledger_entries",
        ["user_id", "reason", "reference_day"],
        unique=True,
    )

    op.create_table(
        "app_settings",
        _id_column(),
        sa.Column(
            "minimum_first_deposit",
            sa.Numeric(precision=14, scale=2),
            server_default="10",
            nullable=False,
        ),
        sa.Column(
            "premium_minimum_deposit",
            sa.Numeric(precision=14, scale=2),
            server_default="100",
            nullable=False,
        ),
        sa.Column(
            "premium_daily_limit", sa.Integer(), server_default="10", nullable=False
        ),
        sa.Column("manager_telegram_url", sa.String(length=1024)),
        *_timestamps(),
        sa.CheckConstraint(
            "minimum_first_deposit > 0",
            name=op.f("app_settings_minimum_deposit_positive_check"),
        ),
        sa.CheckConstraint(
            "premium_minimum_deposit > 0",
            name=op.f("app_settings_premium_deposit_positive_check"),
        ),
        sa.CheckConstraint(
            "premium_daily_limit >= 0",
            name=op.f("app_settings_premium_limit_nonnegative_check"),
        ),
    )

    op.create_table(
        "products",
        "app_settings",
        _id_column(),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("description", sa.Text()),
        sa.Column("product_type", sa.String(length=16), nullable=False),
        sa.Column("price_pac", sa.Numeric(precision=14, scale=2)),
        sa.Column(
            "grant_condition",
            sa.String(length=32),
            server_default="none",
            nullable=False,
        ),
        sa.Column("grant_deposit_threshold", sa.Numeric(precision=14, scale=2)),
        sa.Column("external_url", sa.Text()),
        sa.Column(
            "is_published", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "product_type IN ('course', 'module', 'group', 'bot')",
            name=op.f("products_type_known_check"),
        ),
        sa.CheckConstraint(
            "grant_condition IN ('none', 'registration', 'deposit_threshold')",
            name=op.f("products_grant_condition_known_check"),
        ),
        sa.CheckConstraint(
            "price_pac IS NULL OR price_pac >= 0",
            name=op.f("products_price_nonnegative_check"),
        ),
        sa.CheckConstraint(
            "grant_condition <> 'deposit_threshold' OR grant_deposit_threshold IS NOT NULL",
            name=op.f("products_threshold_required_check"),
        ),
    )
    op.create_table(
        "product_materials",
        _id_column(),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("content_type", sa.String(length=32), nullable=False),
        sa.Column("storage_key", sa.String(length=1024)),
        sa.Column("external_url", sa.Text()),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        *_timestamps(),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
    )
    op.create_index(
        op.f("product_materials_product_id_idx"), "product_materials", ["product_id"]
    )
    op.create_index(
        "product_materials_product_order_idx",
        "product_materials",
        ["product_id", "sort_order"],
    )
    op.create_table(
        "user_product_accesses",
        _id_column(),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("product_id", sa.UUID(), nullable=False),
        sa.Column("source", sa.String(length=16), nullable=False),
        sa.Column("purchase_price_pac", sa.Numeric(precision=14, scale=2)),
        *_timestamps(),
        sa.CheckConstraint(
            "source IN ('purchase', 'automatic', 'manual')",
            name=op.f("user_product_accesses_source_known_check"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["product_id"], ["products.id"], ondelete="CASCADE"),
    )
    op.create_index(
        op.f("user_product_accesses_user_id_idx"), "user_product_accesses", ["user_id"]
    )
    op.create_index(
        op.f("user_product_accesses_product_id_idx"),
        "user_product_accesses",
        ["product_id"],
    )
    op.create_index(
        "user_product_accesses_user_product_key",
        "user_product_accesses",
        ["user_id", "product_id"],
        unique=True,
    )

    op.create_table(
        "signal_assets",
        _id_column(),
        sa.Column("asset_key", sa.String(length=64), nullable=False),
        sa.Column("label", sa.String(length=128), nullable=False),
        sa.Column("category", sa.String(length=64), nullable=False),
        sa.Column(
            "is_otc", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "is_popular", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column(
            "is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False
        ),
        sa.Column("sort_order", sa.Integer(), server_default="0", nullable=False),
        *_timestamps(),
    )
    op.create_index(
        "signal_assets_key_key", "signal_assets", ["asset_key"], unique=True
    )
    op.create_table(
        "signals",
        _id_column(),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("signal_asset_id", sa.UUID(), nullable=False),
        sa.Column("asset_label", sa.String(length=128), nullable=False),
        sa.Column("timeframe_seconds", sa.Integer(), nullable=False),
        sa.Column("direction", sa.String(length=8), nullable=False),
        sa.Column("probability", sa.Integer(), nullable=False),
        sa.Column(
            "is_premium", sa.Boolean(), server_default=sa.text("false"), nullable=False
        ),
        sa.Column("requested_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "direction IN ('buy', 'sell')",
            name=op.f("signals_direction_known_check"),
        ),
        sa.CheckConstraint(
            "timeframe_seconds > 0",
            name=op.f("signals_timeframe_positive_check"),
        ),
        sa.CheckConstraint(
            "probability BETWEEN 0 AND 100",
            name=op.f("signals_probability_valid_check"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(
            ["signal_asset_id"], ["signal_assets.id"], ondelete="RESTRICT"
        ),
    )
    op.create_index(op.f("signals_user_id_idx"), "signals", ["user_id"])
    op.create_index(
        "signals_user_requested_idx", "signals", ["user_id", "requested_at"]
    )

    op.create_table(
        "notifications",
        _id_column(),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("notification_type", sa.String(length=32), nullable=False),
        sa.Column("title", sa.String(length=255), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("read_at", sa.DateTime(timezone=True)),
        *_timestamps(),
        sa.CheckConstraint(
            "notification_type IN ('registration', 'deposit', 'product_access', "
            "'status_changed', 'access_blocked', 'access_restored', "
            "'low_first_deposit', 'diary_reminder')",
            name=op.f("notifications_type_known_check"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("notifications_user_id_idx"), "notifications", ["user_id"])
    op.create_index(
        "notifications_user_read_created_idx",
        "notifications",
        ["user_id", "read_at", "created_at"],
    )
    op.create_table(
        "diary_entries",
        _id_column(),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("entry_day", sa.Date(), nullable=False),
        sa.Column("profitable_trades", sa.Integer(), nullable=False),
        sa.Column("losing_trades", sa.Integer(), nullable=False),
        sa.Column("mood", sa.Integer(), nullable=False),
        sa.Column("comment", sa.Text()),
        *_timestamps(),
        sa.CheckConstraint(
            "profitable_trades >= 0",
            name=op.f("diary_entries_profitable_nonnegative_check"),
        ),
        sa.CheckConstraint(
            "losing_trades >= 0",
            name=op.f("diary_entries_losing_nonnegative_check"),
        ),
        sa.CheckConstraint(
            "mood BETWEEN 1 AND 5", name=op.f("diary_entries_mood_valid_check")
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("diary_entries_user_id_idx"), "diary_entries", ["user_id"])
    op.create_index(
        "diary_entries_user_day_key",
        "diary_entries",
        ["user_id", "entry_day"],
        unique=True,
    )
    op.create_table(
        "user_activities",
        _id_column(),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("activity_type", sa.String(length=32), nullable=False),
        sa.Column("occurred_at", sa.DateTime(timezone=True), nullable=False),
        *_timestamps(),
        sa.CheckConstraint(
            "activity_type IN ('webapp_opened', 'signal_generated')",
            name=op.f("user_activities_type_known_check"),
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
    )
    op.create_index(op.f("user_activities_user_id_idx"), "user_activities", ["user_id"])
    op.create_index(
        "user_activities_type_occurred_idx",
        "user_activities",
        ["activity_type", "occurred_at"],
    )
    op.create_table(
        "audit_logs",
        _id_column(),
        sa.Column("actor_id", sa.UUID()),
        sa.Column("target_user_id", sa.UUID()),
        sa.Column("action", sa.String(length=64), nullable=False),
        sa.Column(
            "payload",
            postgresql.JSONB(),
            server_default=sa.text("'{}'::jsonb"),
            nullable=False,
        ),
        *_timestamps(),
        sa.ForeignKeyConstraint(["actor_id"], ["users.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["target_user_id"], ["users.id"], ondelete="SET NULL"),
    )
    op.create_index(op.f("audit_logs_actor_id_idx"), "audit_logs", ["actor_id"])
    op.create_index(
        op.f("audit_logs_target_user_id_idx"), "audit_logs", ["target_user_id"]
    )
    op.create_index(
        "audit_logs_actor_created_idx", "audit_logs", ["actor_id", "created_at"]
    )


def downgrade() -> None:
    for table_name in (
        "audit_logs",
        "user_activities",
        "diary_entries",
        "notifications",
        "signals",
        "signal_assets",
        "user_product_accesses",
        "product_materials",
        "products",
        "pac_ledger_entries",
        "withdrawals",
        "deposits",
        "broker_accounts",
        "external_events",
        "attribution_clicks",
        "users",
    ):
        op.drop_table(table_name)
