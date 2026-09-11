import datetime

from sqlalchemy import BigInteger, DateTime, Index, String, Text
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base
from database.fields import uuid_pk


class AttributionClick(Base):
    __tablename__ = "attribution_clicks"
    __table_args__ = (
        Index("attribution_clicks_telegram_recorded_idx", "telegram_id", "recorded_at"),
    )

    id: Mapped[uuid_pk]
    telegram_id: Mapped[int] = mapped_column(BigInteger, index=True)
    click_id: Mapped[str] = mapped_column(String(255), unique=True)
    link_chat: Mapped[str | None] = mapped_column(Text)
    source_created_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    recorded_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))


class ExternalEvent(Base):
    __tablename__ = "external_events"
    __table_args__ = (
        Index(
            "external_events_provider_type_occurred_idx",
            "provider",
            "event_type",
            "occurred_at",
        ),
    )

    id: Mapped[uuid_pk]
    provider: Mapped[str] = mapped_column(String(32))
    event_type: Mapped[str] = mapped_column(String(32))
    deduplication_key: Mapped[str] = mapped_column(String(128), unique=True)
    source_event_id: Mapped[str | None] = mapped_column(String(255), index=True)
    processing_status: Mapped[str] = mapped_column(String(16), index=True)
    payload: Mapped[dict] = mapped_column(JSONB)
    occurred_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    received_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
    processed_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True)
    )
    rejection_reason: Mapped[str | None] = mapped_column(Text)
