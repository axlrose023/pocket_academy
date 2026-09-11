from typing import Self, Any

from sqlalchemy.ext.asyncio import AsyncSession

from database.dao.user_dao import UserDAO


class UnitOfWork:
    session: AsyncSession
    user_dao: UserDAO

    def __init__(self: Self, session: AsyncSession):
        self.session = session
        self.user_dao = UserDAO(session)

    async def commit(self: Self):
        await self.session.commit()

    async def flush(self: Self):
        await self.session.flush()

    async def refresh(self: Self, instance: Any):
        await self.session.refresh(instance)

    async def rollback(self: Self):
        await self.session.rollback()

    async def close(self: Self):
        await self.session.close()

    async def __aenter__(self: Self) -> Self:
        return self

    async def __aexit__(self: Self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        await self.close()
