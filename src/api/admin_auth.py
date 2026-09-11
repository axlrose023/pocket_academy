from dataclasses import dataclass

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import Depends, HTTPException, status

from api.webapp_auth import WebAppContext, get_webapp_context
from database.models import User
from services.admin import AdminPermissionError, AdminService


@dataclass(frozen=True, slots=True)
class AdminContext:
    webapp: WebAppContext
    user: User


@inject
async def get_admin_context(
    admin_service: FromDishka[AdminService],
    webapp: WebAppContext = Depends(get_webapp_context),
) -> AdminContext:
    try:
        user = await admin_service.require_admin(
            webapp.uow,
            telegram_id=webapp.user.telegram_id,
        )
    except AdminPermissionError as error:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Administrator access is required",
        ) from error
    return AdminContext(webapp=webapp, user=user)
