from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException, status

from api.schemas import TelegramSessionRequest, TelegramSessionResponse
from database.uow import UnitOfWork
from domain.clock import Clock
from services import TelegramWebAppAuthService, UserService
from services.exceptions import TelegramInitDataError

router = APIRouter(tags=["authentication"])


@router.post("/auth/telegram", response_model=TelegramSessionResponse)
@inject
async def authenticate_telegram_webapp(
    payload: TelegramSessionRequest,
    uow: FromDishka[UnitOfWork],
    auth_service: FromDishka[TelegramWebAppAuthService],
    user_service: FromDishka[UserService],
    clock: FromDishka[Clock],
) -> TelegramSessionResponse:
    try:
        profile = auth_service.verify(payload.init_data)
    except TelegramInitDataError as error:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid Telegram credentials",
        ) from error
    user = await user_service.register_or_update(
        uow,
        profile=profile,
        seen_at=clock.now(),
    )
    await uow.commit()
    return TelegramSessionResponse(
        telegram_id=user.telegram_id,
        first_name=user.first_name,
    )
