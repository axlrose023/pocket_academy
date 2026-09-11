from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AppSettings


class SettingsDAO:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self) -> AppSettings:
        settings = await self._session.scalar(select(AppSettings).limit(1))
        if settings is not None:
            return settings
        settings = AppSettings()
        self._session.add(settings)
        await self._session.flush()
        return settings
