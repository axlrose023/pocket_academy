"""Notify users about diary streak rewards.

Revision ID: d4e5f6a7b8c9
Revises: 9c1d2e3f4a5b
Create Date: 2026-09-21 11:00:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "d4e5f6a7b8c9"
down_revision: str | None = "9c1d2e3f4a5b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.drop_constraint(
        op.f("notifications_type_known_check"), "notifications", type_="check"
    )
    op.create_check_constraint(
        op.f("notifications_type_known_check"),
        "notifications",
        "notification_type IN ('registration', 'deposit', 'product_access', "
        "'status_changed', 'access_blocked', 'access_restored', "
        "'low_first_deposit', 'diary_reminder', 'diary_streak_reward')",
    )
    op.execute(
        """
        INSERT INTO notifications (
            user_id, notification_type, title, body, reminder_day, created_at, updated_at
        )
        SELECT
            ledger.user_id,
            'diary_streak_reward',
            'Бонус начислен',
            'За дневник два дня подряд начислено 5 PAC.',
            ledger.reference_day,
            ledger.created_at,
            ledger.created_at
        FROM pac_ledger_entries AS ledger
        WHERE ledger.reason = 'diary_streak_reward'
        ON CONFLICT (user_id, notification_type, reminder_day) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        "DELETE FROM notifications WHERE notification_type = 'diary_streak_reward'"
    )
    op.drop_constraint(
        op.f("notifications_type_known_check"), "notifications", type_="check"
    )
    op.create_check_constraint(
        op.f("notifications_type_known_check"),
        "notifications",
        "notification_type IN ('registration', 'deposit', 'product_access', "
        "'status_changed', 'access_blocked', 'access_restored', "
        "'low_first_deposit', 'diary_reminder')",
    )
