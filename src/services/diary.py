import datetime
import uuid
from dataclasses import dataclass
from decimal import Decimal

from database.models import DiaryEntry
from database.uow import UnitOfWork
from domain.enums import PacEntryReason


@dataclass(frozen=True, slots=True)
class DiarySaveResult:
    entry: DiaryEntry
    reward_granted: bool


class DiaryService:
    async def save_today(
        self,
        uow: UnitOfWork,
        *,
        user_id: uuid.UUID,
        today: datetime.date,
        profitable_trades: int,
        losing_trades: int,
        mood: int,
        comment: str | None,
    ) -> DiarySaveResult:
        if await uow.users.get_for_update(user_id) is None:
            raise ValueError("User not found")
        entry = await uow.engagement.save_diary_entry(
            user_id=user_id,
            entry_day=today,
            profitable_trades=profitable_trades,
            losing_trades=losing_trades,
            mood=mood,
            comment=comment,
        )
        if not await uow.engagement.has_diary_entry(
            user_id=user_id,
            entry_day=today - datetime.timedelta(days=1),
        ):
            return DiarySaveResult(entry=entry, reward_granted=False)
        reward_granted = await uow.pac_ledger.add_daily_reward_once(
            user_id=user_id,
            amount=Decimal("5"),
            reason=PacEntryReason.DIARY_STREAK_REWARD.value,
            reference_day=today,
            note="Two-day diary streak",
        )
        return DiarySaveResult(entry=entry, reward_granted=reward_granted)
