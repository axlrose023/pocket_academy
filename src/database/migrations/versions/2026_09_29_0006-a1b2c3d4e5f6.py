"""Add products included in a course bundle.

Revision ID: a1b2c3d4e5f6
Revises: d4e5f6a7b8c9
Create Date: 2026-09-29 16:50:00.000000
"""

from collections.abc import Sequence

import sqlalchemy as sa
from alembic import op

revision: str = "a1b2c3d4e5f6"
down_revision: str | None = "d4e5f6a7b8c9"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "product_bundle_items",
        sa.Column(
            "id",
            sa.UUID(),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("bundle_product_id", sa.UUID(), nullable=False),
        sa.Column("included_product_id", sa.UUID(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.Column(
            "updated_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("CURRENT_TIMESTAMP"),
        ),
        sa.CheckConstraint(
            "bundle_product_id <> included_product_id",
            name=op.f("product_bundle_items_different_products_check"),
        ),
        sa.ForeignKeyConstraint(
            ["bundle_product_id"], ["products.id"], ondelete="CASCADE"
        ),
        sa.ForeignKeyConstraint(
            ["included_product_id"], ["products.id"], ondelete="CASCADE"
        ),
        sa.UniqueConstraint(
            "bundle_product_id",
            "included_product_id",
            name="product_bundle_item_unique",
        ),
    )
    op.create_index(
        op.f("product_bundle_items_bundle_product_id_idx"),
        "product_bundle_items",
        ["bundle_product_id"],
    )
    op.create_index(
        op.f("product_bundle_items_included_product_id_idx"),
        "product_bundle_items",
        ["included_product_id"],
    )


def downgrade() -> None:
    op.drop_index(
        op.f("product_bundle_items_included_product_id_idx"),
        table_name="product_bundle_items",
    )
    op.drop_index(
        op.f("product_bundle_items_bundle_product_id_idx"),
        table_name="product_bundle_items",
    )
    op.drop_table("product_bundle_items")
