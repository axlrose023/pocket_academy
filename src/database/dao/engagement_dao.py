import datetime
import uuid

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import DiaryEntry, Notification


class EngagementDAO:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def save_diary_entry(
        self,
        *,
        user_id: uuid.UUID,
        entry_day: datetime.date,
        profitable_trades: int,
        losing_trades: int,
        mood: int,
        comment: str | None,
    ) -> DiaryEntry:
        statement = insert(DiaryEntry).values(
            user_id=user_id,
            entry_day=entry_day,
            profitable_trades=profitable_trades,
            losing_trades=losing_trades,
            mood=mood,
            comment=comment,
        )
        statement = statement.on_conflict_do_update(
            index_elements=[DiaryEntry.user_id, DiaryEntry.entry_day],
            set_={
                "profitable_trades": statement.excluded.profitable_trades,
                "losing_trades": statement.excluded.losing_trades,
                "mood": statement.excluded.mood,
                "comment": statement.excluded.comment,
            },
        ).returning(DiaryEntry)
        return (await self._session.execute(statement)).scalar_one()

    async def has_diary_entry(
        self, *, user_id: uuid.UUID, entry_day: datetime.date
    ) -> bool:
        return (
            await self._session.scalar(
                select(DiaryEntry.id).where(
                    DiaryEntry.user_id == user_id,
                    DiaryEntry.entry_day == entry_day,
                )
            )
            is not None
        )

    async def add_notification(
        self,
        *,
        user_id: uuid.UUID,
        notification_type: str,
        title: str,
        body: str,
    ) -> Notification:
        notification = Notification(
            user_id=user_id,
            notification_type=notification_type,
            title=title,
            body=body,
        )
        self._session.add(notification)
        return notification
