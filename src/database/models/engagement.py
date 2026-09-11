import datetime
import uuid

from sqlalchemy import (
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base
from database.fields import uuid_pk


class Notification(Base):
    __tablename__ = "notifications"
    __table_args__ = (
        Index(
            "notifications_user_read_created_idx", "user_id", "read_at", "created_at"
        ),
        Index(
            "notifications_diary_reminder_day_key",
            "user_id",
            "notification_type",
            "reminder_day",
            unique=True,
        ),
        CheckConstraint(
            "notification_type IN ('registration', 'deposit', 'product_access', "
            "'status_changed', 'access_blocked', 'access_restored', "
            "'low_first_deposit', 'diary_reminder')",
            name="type_known",
        ),
    )

    id: Mapped[uuid_pk]
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    notification_type: Mapped[str] = mapped_column(String(32))
    title: Mapped[str] = mapped_column(String(255))
    body: Mapped[str] = mapped_column(Text)
    reminder_day: Mapped[datetime.date | None] = mapped_column(Date)
    read_at: Mapped[datetime.datetime | None] = mapped_column(DateTime(timezone=True))


class DiaryEntry(Base):
    __tablename__ = "diary_entries"
    __table_args__ = (
        Index("diary_entries_user_day_key", "user_id", "entry_day", unique=True),
        CheckConstraint("profitable_trades >= 0", name="profitable_nonnegative"),
        CheckConstraint("losing_trades >= 0", name="losing_nonnegative"),
        CheckConstraint("mood BETWEEN 1 AND 5", name="mood_valid"),
    )

    id: Mapped[uuid_pk]
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    entry_day: Mapped[datetime.date] = mapped_column(Date)
    profitable_trades: Mapped[int] = mapped_column(Integer)
    losing_trades: Mapped[int] = mapped_column(Integer)
    mood: Mapped[int] = mapped_column(Integer)
    comment: Mapped[str | None] = mapped_column(Text)


class UserActivity(Base):
    __tablename__ = "user_activities"
    __table_args__ = (
        Index("user_activities_type_occurred_idx", "activity_type", "occurred_at"),
        CheckConstraint(
            "activity_type IN ('webapp_opened', 'signal_generated')", name="type_known"
        ),
    )

    id: Mapped[uuid_pk]
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    activity_type: Mapped[str] = mapped_column(String(32))
    occurred_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
