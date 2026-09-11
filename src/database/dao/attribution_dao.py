import datetime

from sqlalchemy.dialects.postgresql import insert
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AttributionClick


class AttributionDAO:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def upsert(
        self,
        *,
        telegram_id: int,
        click_id: str,
        link_chat: str | None,
        source_created_at: datetime.datetime | None,
        recorded_at: datetime.datetime,
    ) -> AttributionClick:
        statement = insert(AttributionClick).values(
            telegram_id=telegram_id,
            click_id=click_id,
            link_chat=link_chat,
            source_created_at=source_created_at,
            recorded_at=recorded_at,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[AttributionClick.click_id],
            set_={
                "telegram_id": statement.excluded.telegram_id,
                "link_chat": statement.excluded.link_chat,
                "source_created_at": statement.excluded.source_created_at,
                "recorded_at": statement.excluded.recorded_at,
            },
        ).returning(AttributionClick)
        return (await self._session.execute(statement)).scalar_one()

    async def get_by_click_id(self, click_id: str) -> AttributionClick | None:
        return await self._session.scalar(
            select(AttributionClick).where(AttributionClick.click_id == click_id)
        )
