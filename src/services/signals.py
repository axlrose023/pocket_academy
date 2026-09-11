import datetime
import uuid
from dataclasses import dataclass

from database.models import Signal, User
from database.uow import UnitOfWork
from domain.clock import Clock
from domain.randomizer import SignalRandomizer
from domain.statuses import allowed_timeframes
from services.access import AccessService


class SignalRuleError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SignalAvailability:
    used: int
    limit: int | None
    next_available_at: datetime.datetime | None


class SignalService:
    def __init__(
        self, clock: Clock, randomizer: SignalRandomizer, access_service: AccessService
    ) -> None:
        self._clock = clock
        self._randomizer = randomizer
        self._access_service = access_service

    async def generate(
        self,
        uow: UnitOfWork,
        *,
        user_id: uuid.UUID,
        asset_id: uuid.UUID,
        timeframe_seconds: int,
        premium: bool,
    ) -> Signal:
        user = await uow.session.get(User, user_id)
        if user is None:
            raise SignalRuleError("User not found")
        access = await self._access_service.snapshot(uow, user=user)
        if access.is_blocked:
            raise SignalRuleError("Access is blocked")
        if timeframe_seconds not in allowed_timeframes(access.status_policy):
            raise SignalRuleError("Timeframe is not available")
        now = self._clock.now()
        settings = await uow.settings.get_or_create()
        availability = await self.availability(
            uow,
            user_id=user_id,
            premium=premium,
            daily_limit=(
                settings.premium_daily_limit
                if premium
                else access.status_policy.daily_signal_limit
            ),
            wait_seconds=5 if premium else access.status_policy.signal_wait_seconds,
        )
        if availability.limit is not None and availability.used >= availability.limit:
            raise SignalRuleError("Daily signal limit reached")
        if availability.next_available_at and availability.next_available_at > now:
            raise SignalRuleError("Signal wait is active")
        asset = await uow.signals.get_active_asset(asset_id)
        if asset is None:
            raise SignalRuleError("Signal asset is unavailable")
        if premium:
            if access.total_deposits < settings.premium_minimum_deposit:
                raise SignalRuleError("Premium signal requires a larger deposit")
        return await uow.signals.add(
            user_id=user_id,
            asset=asset,
            timeframe_seconds=timeframe_seconds,
            direction=self._randomizer.direction().value,
            probability=self._randomizer.probability(
                access.status_policy, premium=premium
            ),
            premium=premium,
            requested_at=now,
        )

    async def availability(
        self,
        uow: UnitOfWork,
        *,
        user_id: uuid.UUID,
        premium: bool,
        daily_limit: int | None,
        wait_seconds: int,
    ) -> SignalAvailability:
        now = self._clock.now()
        day_start = now.replace(hour=0, minute=0, second=0, microsecond=0)
        next_day = day_start + datetime.timedelta(days=1)
        used = await uow.signals.count_requested(
            user_id, premium=premium, since=day_start, until=next_day
        )
        last_requested_at = await uow.signals.last_requested_at(
            user_id, premium=premium
        )
        next_available_at = (
            last_requested_at + datetime.timedelta(seconds=wait_seconds)
            if last_requested_at is not None
            else None
        )
        return SignalAvailability(
            used=used,
            limit=daily_limit,
            next_available_at=next_available_at,
        )
