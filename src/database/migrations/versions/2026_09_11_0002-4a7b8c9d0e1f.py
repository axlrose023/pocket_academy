"""Add idempotent diary reminder delivery.

Revision ID: 4a7b8c9d0e1f
Revises: 5f36d88c6b47
Create Date: 2026-09-11 00:02:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "4a7b8c9d0e1f"
down_revision: str | None = "5f36d88c6b47"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "notifications",
        sa.Column("reminder_day", sa.Date(), nullable=True),
    )
    op.create_index(
        "notifications_diary_reminder_day_key",
        "notifications",
        ["user_id", "notification_type", "reminder_day"],
        unique=True,
    )


def downgrade() -> None:
    op.drop_index("notifications_diary_reminder_day_key", table_name="notifications")
    op.drop_column("notifications", "reminder_day")
