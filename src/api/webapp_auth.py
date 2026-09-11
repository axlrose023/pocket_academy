from dataclasses import dataclass

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import Header, HTTPException, status

from database.models import User
from database.uow import UnitOfWork
from domain.clock import Clock
from services import TelegramWebAppAuthService, UserService
from services.exceptions import TelegramInitDataError


@dataclass(frozen=True, slots=True)
class WebAppContext:
    uow: UnitOfWork
    user: User
    clock: Clock


async def current_webapp_user(
    uow: UnitOfWork,
    auth_service: TelegramWebAppAuthService,
    user_service: UserService,
    clock: Clock,
    init_data: str | None,
) -> User:
    if not init_data:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Missing Telegram credentials",
        )
    try:
        profile = auth_service.verify(init_data)
    except TelegramInitDataError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram credentials",
        ) from error
    user = await user_service.register_or_update(
        uow, profile=profile, seen_at=clock.now()
    )
    await uow.commit()
    return user


@inject
async def get_webapp_context(
    uow: FromDishka[UnitOfWork],
    auth_service: FromDishka[TelegramWebAppAuthService],
    user_service: FromDishka[UserService],
    clock: FromDishka[Clock],
    init_data: str | None = Header(default=None, alias="X-Telegram-Init-Data"),
) -> WebAppContext:
    user = await current_webapp_user(uow, auth_service, user_service, clock, init_data)
    return WebAppContext(uow=uow, user=user, clock=clock)
