import datetime

from database.models import User
from database.uow import UnitOfWork
from services.telegram_auth import TelegramWebAppUser


class UserService:
    async def register_or_update(
        self,
        uow: UnitOfWork,
        *,
        profile: TelegramWebAppUser,
        seen_at: datetime.datetime,
    ) -> User:
        return await uow.users.upsert_profile(
            telegram_id=profile.telegram_id,
            username=profile.username,
            first_name=profile.first_name,
            last_name=profile.last_name,
            language_code=profile.language_code,
            last_seen_at=seen_at,
        )
