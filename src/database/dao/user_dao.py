from typing import Self

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models.user import User


class UserDAO:
    def __init__(self: Self, session: AsyncSession) -> None:
        self.session = session

    async def get_by_chat_id(self: Self, chat_id: int) -> User | None:
        stmt = select(User).where(User.chat_id == chat_id)
        query = await self.session.execute(stmt)
        return query.scalar_one_or_none()

    async def create(
        self: Self,
        chat_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
    ) -> User:
        user = User(
            chat_id=chat_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
        )
        self.session.add(user)
        return user
