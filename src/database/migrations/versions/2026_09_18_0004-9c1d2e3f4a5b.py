"""Add per-user test access.

Revision ID: 9c1d2e3f4a5b
Revises: 7b2c4d6e8f01
Create Date: 2026-09-18 00:04:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "9c1d2e3f4a5b"
down_revision: str | None = "7b2c4d6e8f01"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_test_access",
            sa.Boolean(),
            nullable=False,
            server_default=sa.text("false"),
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_test_access")
