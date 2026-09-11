import datetime
import uuid

from sqlalchemy import exists, literal, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import DiaryEntry, Notification, User, UserActivity


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

    async def list_diary_entries(
        self, *, user_id: uuid.UUID, limit: int
    ) -> list[DiaryEntry]:
        return list(
            (
                await self._session.scalars(
                    select(DiaryEntry)
                    .where(DiaryEntry.user_id == user_id)
                    .order_by(DiaryEntry.entry_day.desc())
                    .limit(limit)
                )
            ).all()
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

    async def add_diary_reminders(self, *, entry_day: datetime.date) -> int:
        missing_entry = ~exists(
            select(DiaryEntry.id).where(
                DiaryEntry.user_id == User.id,
                DiaryEntry.entry_day == entry_day,
            )
        )
        recipients = select(
            User.id,
            literal("diary_reminder"),
            literal("Trading diary reminder"),
            literal("Fill in today's diary entry and keep your PAC streak going."),
            literal(entry_day),
        ).where(User.last_seen_at.is_not(None), missing_entry)
        statement = insert(Notification).from_select(
            [
                Notification.user_id,
                Notification.notification_type,
                Notification.title,
                Notification.body,
                Notification.reminder_day,
            ],
            recipients,
        )
        result = await self._session.execute(
            statement.on_conflict_do_nothing(
                index_elements=[
                    Notification.user_id,
                    Notification.notification_type,
                    Notification.reminder_day,
                ]
            )
        )
        return int(result.rowcount or 0)

    async def add_activity(
        self,
        *,
        user_id: uuid.UUID,
        activity_type: str,
        occurred_at: datetime.datetime,
    ) -> UserActivity:
        activity = UserActivity(
            user_id=user_id,
            activity_type=activity_type,
            occurred_at=occurred_at,
        )
        self._session.add(activity)
        return activity

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
