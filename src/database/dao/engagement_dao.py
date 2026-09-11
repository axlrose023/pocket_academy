import datetime
import uuid

from sqlalchemy import select, update
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

    async def get_diary_entry(
        self, *, user_id: uuid.UUID, entry_day: datetime.date
    ) -> DiaryEntry | None:
        return await self._session.scalar(
            select(DiaryEntry).where(
                DiaryEntry.user_id == user_id,
                DiaryEntry.entry_day == entry_day,
            )
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

    async def list_notifications(
        self, *, user_id: uuid.UUID, limit: int
    ) -> list[Notification]:
        return list(
            (
                await self._session.scalars(
                    select(Notification)
                    .where(Notification.user_id == user_id)
                    .order_by(Notification.created_at.desc())
                    .limit(limit)
                )
            ).all()
        )

    async def mark_notifications_read(
        self, *, user_id: uuid.UUID, read_at: datetime.datetime
    ) -> int:
        result = await self._session.execute(
            update(Notification)
            .where(
                Notification.user_id == user_id,
                Notification.read_at.is_(None),
            )
            .values(read_at=read_at)
        )
        return int(result.rowcount or 0)
