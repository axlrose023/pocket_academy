import datetime
import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, DateTime, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base
from database.fields import uuid_pk


class BrokerAccount(Base):
    __tablename__ = "broker_accounts"
    __table_args__ = (
        Index(
            "broker_accounts_provider_trader_key", "provider", "trader_id", unique=True
        ),
    )

    id: Mapped[uuid_pk]
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    attribution_click_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("attribution_clicks.id", ondelete="SET NULL"),
    )
    provider: Mapped[str] = mapped_column(String(32))
    trader_id: Mapped[str] = mapped_column(String(255))
    registered_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))


class Deposit(Base):
    __tablename__ = "deposits"
    __table_args__ = (
        Index("deposits_user_occurred_idx", "user_id", "occurred_at"),
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint("kind IN ('first', 'repeat')", name="kind_known"),
    )

    id: Mapped[uuid_pk]
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    broker_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("broker_accounts.id", ondelete="CASCADE"),
        index=True,
    )
    external_event_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("external_events.id", ondelete="RESTRICT"),
        unique=True,
    )
    kind: Mapped[str] = mapped_column(String(16))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    occurred_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))


class Withdrawal(Base):
    __tablename__ = "withdrawals"
    __table_args__ = (
        Index(
            "withdrawals_user_status_requested_idx", "user_id", "status", "requested_at"
        ),
        Index(
            "withdrawals_provider_reference_key",
            "provider",
            "external_reference",
            unique=True,
        ),
        CheckConstraint("amount > 0", name="amount_positive"),
        CheckConstraint(
            "status IN ('new', 'cancelled', 'success')", name="status_known"
        ),
    )

    id: Mapped[uuid_pk]
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    broker_account_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("broker_accounts.id", ondelete="CASCADE"),
        index=True,
    )
    last_external_event_id: Mapped[uuid.UUID | None] = mapped_column(
        ForeignKey("external_events.id", ondelete="SET NULL"),
    )
    provider: Mapped[str] = mapped_column(String(32))
    external_reference: Mapped[str] = mapped_column(String(255))
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    status: Mapped[str] = mapped_column(String(16))
    requested_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    resolved_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
