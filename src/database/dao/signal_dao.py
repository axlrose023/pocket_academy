import datetime
import uuid

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Signal, SignalAsset


class SignalDAO:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_active_asset(self, asset_id: uuid.UUID) -> SignalAsset | None:
        return await self._session.scalar(
            select(SignalAsset).where(
                SignalAsset.id == asset_id,
                SignalAsset.is_active.is_(True),
            )
        )

    async def last_requested_at(
        self, user_id: uuid.UUID, *, premium: bool
    ) -> datetime.datetime | None:
        return await self._session.scalar(
            select(func.max(Signal.requested_at)).where(
                Signal.user_id == user_id,
                Signal.is_premium.is_(premium),
            )
        )

    async def count_requested(
        self,
        user_id: uuid.UUID,
        *,
        premium: bool,
        since: datetime.datetime,
        until: datetime.datetime,
    ) -> int:
        return int(
            await self._session.scalar(
                select(func.count()).where(
                    Signal.user_id == user_id,
                    Signal.is_premium.is_(premium),
                    Signal.requested_at >= since,
                    Signal.requested_at < until,
                )
            )
            or 0
        )

    async def add(
        self,
        *,
        user_id: uuid.UUID,
        asset: SignalAsset,
        timeframe_seconds: int,
        direction: str,
        probability: int,
        premium: bool,
        requested_at: datetime.datetime,
    ) -> Signal:
        signal = Signal(
            user_id=user_id,
            signal_asset_id=asset.id,
            asset_label=asset.label,
            timeframe_seconds=timeframe_seconds,
            direction=direction,
            probability=probability,
            is_premium=premium,
            requested_at=requested_at,
        )
        self._session.add(signal)
        return signal
