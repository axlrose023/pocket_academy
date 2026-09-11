from collections.abc import AsyncIterator

from aiogram import Bot
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config, get_config
from bot import create_bot
from database.engine import SessionFactory
from database.uow import UnitOfWork


class AppProvider(Provider):
    def __init__(self, config: Config, telegram_bot: Bot | None = None) -> None:
        super().__init__()
        self._config = config
        self._telegram_bot = telegram_bot

    @provide(scope=Scope.APP)
    def get_config(self) -> Config:
        return self._config

    @provide(scope=Scope.REQUEST)
    async def get_session(self) -> AsyncIterator[AsyncSession]:
        async with SessionFactory() as session:
            try:
                yield session
            except Exception:
                await session.rollback()
                raise

    @provide(scope=Scope.REQUEST)
    async def get_uow(self, session: AsyncSession) -> AsyncIterator[UnitOfWork]:
        async with UnitOfWork(session) as uow:
            yield uow

    @provide(scope=Scope.APP)
    def telegram_bot(self) -> Bot:
        if self._telegram_bot is None:
            self._telegram_bot = create_bot(self._config)
        return self._telegram_bot


def get_async_container(
    config: Config | None = None,
    telegram_bot: Bot | None = None,
) -> AsyncContainer:
    return make_async_container(AppProvider(config or get_config(), telegram_bot))
