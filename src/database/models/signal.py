import datetime
import uuid

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
)
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base
from database.fields import uuid_pk


class SignalAsset(Base):
    __tablename__ = "signal_assets"
    __table_args__ = (Index("signal_assets_key_key", "asset_key", unique=True),)

    id: Mapped[uuid_pk]
    asset_key: Mapped[str] = mapped_column(String(64))
    label: Mapped[str] = mapped_column(String(128))
    category: Mapped[str] = mapped_column(String(64))
    is_otc: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    is_popular: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    is_active: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (
        Index("signals_user_requested_idx", "user_id", "requested_at"),
        CheckConstraint("direction IN ('buy', 'sell')", name="direction_known"),
        CheckConstraint("timeframe_seconds > 0", name="timeframe_positive"),
        CheckConstraint("probability BETWEEN 0 AND 100", name="probability_valid"),
    )

    id: Mapped[uuid_pk]
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    signal_asset_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("signal_assets.id", ondelete="RESTRICT")
    )
    asset_label: Mapped[str] = mapped_column(String(128))
    timeframe_seconds: Mapped[int] = mapped_column(Integer)
    direction: Mapped[str] = mapped_column(String(8))
    probability: Mapped[int] = mapped_column(Integer)
    is_premium: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    requested_at: Mapped[datetime.datetime] = mapped_column(DateTime(timezone=True))
