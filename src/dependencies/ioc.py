from collections.abc import AsyncIterator

from aiogram import Bot
from dishka import AsyncContainer, Provider, Scope, make_async_container, provide
from sqlalchemy.ext.asyncio import AsyncSession

from config import Config, get_config
from bot import create_bot
from database.engine import SessionFactory
from database.uow import UnitOfWork
from domain.clock import Clock, SystemClock
from domain.randomizer import SignalRandomizer
from services import (
    AdminService,
    BrokerEventService,
    ChatterfyService,
    DiaryService,
    ExternalEventService,
    PocketOptionEventParser,
    PocketOptionEventService,
    ProductService,
    SignalService,
    TelegramWebAppAuthService,
    UserService,
)
from services.access import AccessService
from services.storage import DisabledMaterialStorage, MaterialStorage, S3MaterialStorage


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
    def pocket_option_event_parser(self, clock: Clock) -> PocketOptionEventParser:
        return PocketOptionEventParser(clock)

    @provide(scope=Scope.APP)
    def access_service(self) -> AccessService:
        return AccessService()

    @provide(scope=Scope.APP)
    def signal_randomizer(self) -> SignalRandomizer:
        return SignalRandomizer()

    @provide(scope=Scope.APP)
    def signal_service(
        self, clock: Clock, randomizer: SignalRandomizer, access_service: AccessService
    ) -> SignalService:
        return SignalService(clock, randomizer, access_service)

    @provide(scope=Scope.APP)
    def product_service(self) -> ProductService:
        return ProductService()

    @provide(scope=Scope.APP)
    def material_storage(self, config: Config) -> MaterialStorage:
        if not config.storage.enabled:
            return DisabledMaterialStorage()
        return S3MaterialStorage(config.storage)

    @provide(scope=Scope.APP)
    def diary_service(self) -> DiaryService:
        return DiaryService()

    @provide(scope=Scope.APP)
    def broker_event_service(
        self,
        product_service: ProductService,
        clock: Clock,
        access_service: AccessService,
    ) -> BrokerEventService:
        return BrokerEventService(product_service, clock, access_service)

    @provide(scope=Scope.APP)
    def pocket_option_event_service(
        self,
        broker_event_service: BrokerEventService,
        parser: PocketOptionEventParser,
    ) -> PocketOptionEventService:
        return PocketOptionEventService(broker_event_service, parser)

    @provide(scope=Scope.APP)
    def admin_service(self, config: Config) -> AdminService:
        return AdminService(config)


def get_async_container(
    config: Config | None = None,
    telegram_bot: Bot | None = None,
) -> AsyncContainer:
    return make_async_container(AppProvider(config or get_config(), telegram_bot))
