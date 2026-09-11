import datetime
import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import PacLedgerEntry


class PacLedgerDAO:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def balance(self, user_id: uuid.UUID) -> Decimal:
        amount = await self._session.scalar(
            select(func.coalesce(func.sum(PacLedgerEntry.amount), 0)).where(
                PacLedgerEntry.user_id == user_id,
            )
        )
        return Decimal(amount)

    async def add(
        self,
        *,
        user_id: uuid.UUID,
        amount: Decimal,
        reason: str,
        reference_day: datetime.date | None = None,
        reference_id: uuid.UUID | None = None,
        note: str | None = None,
    ) -> PacLedgerEntry:
        entry = PacLedgerEntry(
            user_id=user_id,
            amount=amount,
            reason=reason,
            reference_day=reference_day,
            reference_id=reference_id,
            note=note,
        )
        self._session.add(entry)
        return entry

    async def has_entry(
        self, *, user_id: uuid.UUID, reason: str, reference_day: datetime.date
    ) -> bool:
        return (
            await self._session.scalar(
                select(PacLedgerEntry.id).where(
                    PacLedgerEntry.user_id == user_id,
                    PacLedgerEntry.reason == reason,
                    PacLedgerEntry.reference_day == reference_day,
                )
            )
            is not None
        )
