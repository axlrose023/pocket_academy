from typing import Self

import datetime

from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.user import User


class UserDAO:
    def __init__(self: Self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_telegram_id(self: Self, telegram_id: int) -> User | None:
        stmt = select(User).where(User.telegram_id == telegram_id)
        query = await self.session.execute(stmt)
        return query.scalar_one_or_none()

    async def create(
        self: Self,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        language_code: str | None,
    ) -> User:
        user = User(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
        )
        self.session.add(user)
        return user

    async def upsert_profile(
        self,
        *,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        language_code: str | None,
        last_seen_at: datetime.datetime,
    ) -> User:
        statement = insert(User).values(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            last_seen_at=last_seen_at,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[User.telegram_id],
            set_={
                "username": func.coalesce(statement.excluded.username, User.username),
                "first_name": func.coalesce(
                    statement.excluded.first_name, User.first_name
                ),
                "last_name": func.coalesce(
                    statement.excluded.last_name, User.last_name
                ),
                "language_code": func.coalesce(
                    statement.excluded.language_code,
                    User.language_code,
                ),
                "last_seen_at": statement.excluded.last_seen_at,
            },
        ).returning(User)
        return (await self.session.execute(statement)).scalar_one()

    async def ensure_telegram_id(self, telegram_id: int) -> User:
        statement = insert(User).values(telegram_id=telegram_id)
        statement = statement.on_conflict_do_nothing(
            index_elements=[User.telegram_id],
        ).returning(User)
        user = (await self.session.execute(statement)).scalar_one_or_none()
        if user is not None:
            return user
        existing = await self.get_by_telegram_id(telegram_id)
        if existing is None:
            raise RuntimeError("Telegram user was not persisted")
        return existing
