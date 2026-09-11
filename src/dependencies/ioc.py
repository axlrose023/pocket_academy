from collections.abc import AsyncIterator

from aiogram import Bot
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config, get_config
from bot import create_bot
from database.engine import SessionFactory
from database.uow import UnitOfWork
from domain.clock import Clock, SystemClock
from services import (
    ChatterfyService,
    ExternalEventService,
    PocketOptionEventParser,
    TelegramWebAppAuthService,
    UserService,
)


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

    @provide(scope=Scope.APP)
    def clock(self) -> Clock:
        return SystemClock()

    @provide(scope=Scope.APP)
    def telegram_webapp_auth_service(self, config: Config) -> TelegramWebAppAuthService:
        return TelegramWebAppAuthService(config)

    @provide(scope=Scope.APP)
    def user_service(self) -> UserService:
        return UserService()

    @provide(scope=Scope.APP)
    def external_event_service(self, clock: Clock) -> ExternalEventService:
        return ExternalEventService(clock)

    @provide(scope=Scope.APP)
    def chatterfy_service(
        self,
        external_event_service: ExternalEventService,
        clock: Clock,
    ) -> ChatterfyService:
        return ChatterfyService(external_event_service, clock)

    @provide(scope=Scope.APP)
    def pocket_option_event_parser(self) -> PocketOptionEventParser:
        return PocketOptionEventParser()


def get_async_container(
    config: Config | None = None,
    telegram_bot: Bot | None = None,
) -> AsyncContainer:
    return make_async_container(AppProvider(config or get_config(), telegram_bot))
