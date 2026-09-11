from decimal import Decimal

from sqlalchemy import CheckConstraint, Integer, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base
from database.fields import uuid_pk


class AppSettings(Base):
    """Single editable settings record used by the administrator interface."""

    __tablename__ = "app_settings"
    __table_args__ = (
        CheckConstraint("minimum_first_deposit > 0", name="minimum_deposit_positive"),
        CheckConstraint("premium_minimum_deposit > 0", name="premium_deposit_positive"),
        CheckConstraint("premium_daily_limit >= 0", name="premium_limit_nonnegative"),
    )

    id: Mapped[uuid_pk]
    minimum_first_deposit: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("10"),
        server_default="10",
    )
    premium_minimum_deposit: Mapped[Decimal] = mapped_column(
        Numeric(14, 2),
        default=Decimal("100"),
        server_default="100",
    )
    premium_daily_limit: Mapped[int] = mapped_column(
        Integer, default=10, server_default="10"
    )
    manager_telegram_url: Mapped[str | None] = mapped_column(String(1024))
