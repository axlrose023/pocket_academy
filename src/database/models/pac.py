import datetime
import uuid
from decimal import Decimal

from sqlalchemy import CheckConstraint, Date, ForeignKey, Index, Numeric, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base
from database.fields import uuid_pk


class PacLedgerEntry(Base):
    __tablename__ = "pac_ledger_entries"
    __table_args__ = (
        Index("pac_ledger_entries_user_created_idx", "user_id", "created_at"),
        Index(
            "pac_ledger_entries_user_reason_day_key",
            "user_id",
            "reason",
            "reference_day",
            unique=True,
        ),
        CheckConstraint("amount <> 0", name="amount_nonzero"),
        CheckConstraint(
            "reason IN ('deposit', 'product_purchase', 'diary_streak_reward', 'manual_adjustment')",
            name="reason_known",
        ),
    )

    id: Mapped[uuid_pk]
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    amount: Mapped[Decimal] = mapped_column(Numeric(14, 2))
    reason: Mapped[str] = mapped_column(String(32))
    reference_day: Mapped[datetime.date | None] = mapped_column(Date)
    reference_id: Mapped[uuid.UUID | None]
    note: Mapped[str | None] = mapped_column(String(500))
