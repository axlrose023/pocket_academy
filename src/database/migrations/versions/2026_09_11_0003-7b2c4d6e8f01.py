"""Seed Pocket Academy signal assets.

Revision ID: 7b2c4d6e8f01
Revises: 4a7b8c9d0e1f
Create Date: 2026-09-11 00:03:00.000000
"""

from collections.abc import Sequence

from alembic import op

revision: str = "7b2c4d6e8f01"
down_revision: str | None = "4a7b8c9d0e1f"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.execute(
        """
        INSERT INTO signal_assets (
            asset_key, label, category, is_otc, is_popular, is_active, sort_order
        )
        VALUES
            ('EUR/USD', 'EUR/USD', 'forex', false, true, true, 10),
            ('GBP/USD', 'GBP/USD', 'forex', false, true, true, 20),
            ('USD/JPY', 'USD/JPY', 'forex', false, true, true, 30),
            ('EUR/CHF', 'EUR/CHF', 'forex', false, true, true, 40),
            ('EUR/USD_OTC', 'EUR/USD OTC', 'otc', true, true, true, 110),
            ('GBP/USD_OTC', 'GBP/USD OTC', 'otc', true, true, true, 120),
            ('USD/JPY_OTC', 'USD/JPY OTC', 'otc', true, true, true, 130),
            ('EUR/CHF_OTC', 'EUR/CHF OTC', 'otc', true, true, true, 140)
        ON CONFLICT (asset_key) DO NOTHING
        """
    )


def downgrade() -> None:
    op.execute(
        """
        DELETE FROM signal_assets
        WHERE asset_key IN (
            'EUR/USD', 'GBP/USD', 'USD/JPY', 'EUR/CHF',
            'EUR/USD_OTC', 'GBP/USD_OTC', 'USD/JPY_OTC', 'EUR/CHF_OTC'
        )
        """
    )
