"""Add manual access restoration.

Revision ID: 5f36d88c6b47
Revises: 56ec05931fe8
Create Date: 2026-09-11 12:00:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "5f36d88c6b47"
down_revision: str | None = "56ec05931fe8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.add_column(
        "users",
        sa.Column(
            "is_manually_unblocked",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("users", "is_manually_unblocked")
