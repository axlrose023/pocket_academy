import datetime

from sqlalchemy import BigInteger, Boolean, DateTime, String
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base
from database.fields import uuid_pk


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid_pk]

    telegram_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[str | None] = mapped_column(String(64), index=True)
    first_name: Mapped[str | None] = mapped_column(String(255))
    last_name: Mapped[str | None] = mapped_column(String(255))
    language_code: Mapped[str | None] = mapped_column(String(16))
    last_seen_at: Mapped[datetime.datetime | None] = mapped_column(
        DateTime(timezone=True),
        index=True,
    )
    is_admin: Mapped[bool] = mapped_column(
        Boolean, default=False, server_default="false"
    )
    is_manually_blocked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )
    is_manually_unblocked: Mapped[bool] = mapped_column(
        Boolean,
        default=False,
        server_default="false",
    )
    manual_block_reason: Mapped[str | None] = mapped_column(String(500))

    @property
    def full_name(self) -> str:
        return f"{self.first_name or ''} {self.last_name or ''}".strip()
