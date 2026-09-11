from sqlalchemy import BigInteger
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base
from database.fields import uuid_pk


class User(Base):
    __tablename__ = "users"

    id: Mapped[uuid_pk]

    chat_id: Mapped[int] = mapped_column(BigInteger, unique=True)
    username: Mapped[str | None] = mapped_column(unique=True)
    first_name: Mapped[str | None]
    last_name: Mapped[str | None]

    is_admin: Mapped[bool] = mapped_column(default=False, server_default="False")

    @property
    def full_name(self):
        return f"{self.first_name or ''} {self.last_name or ''}".strip()
