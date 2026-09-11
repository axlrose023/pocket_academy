import datetime

from database.models import User
from database.uow import UnitOfWork
from services.telegram_auth import TelegramWebAppUser


class UserService:
    async def upsert(
        self,
        uow: UnitOfWork,
        *,
        telegram_id: int,
        username: str | None,
        first_name: str | None,
        last_name: str | None,
        language_code: str | None,
        seen_at: datetime.datetime,
    ) -> User:
        return await uow.users.upsert_profile(
            telegram_id=telegram_id,
            username=username,
            first_name=first_name,
            last_name=last_name,
            language_code=language_code,
            last_seen_at=seen_at,
        )

    async def register_or_update(
        self,
        uow: UnitOfWork,
        *,
        profile: TelegramWebAppUser,
        seen_at: datetime.datetime,
    ) -> User:
        return await self.upsert(
            uow,
            telegram_id=profile.telegram_id,
            username=profile.username,
            first_name=profile.first_name,
            last_name=profile.last_name,
            language_code=profile.language_code,
            seen_at=seen_at,
        )
