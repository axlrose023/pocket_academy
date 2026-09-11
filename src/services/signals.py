import datetime
import uuid
from dataclasses import dataclass
from decimal import Decimal

from database.models import Signal, User
from database.uow import UnitOfWork
from domain.clock import Clock
from domain.enums import ActivityType
from domain.randomizer import SignalRandomizer
from domain.statuses import allowed_timeframes
from services.access import AccessService, UserAccessSnapshot


class SignalRuleError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class SignalAvailability:
    used: int
    limit: int | None
    next_available_at: datetime.datetime | None


@dataclass(frozen=True, slots=True)
class UserSignalOverview:
    access: UserAccessSnapshot
    is_registered: bool
    has_deposit: bool
    standard: SignalAvailability
    premium: SignalAvailability
    premium_minimum_deposit: Decimal
    is_premium_available: bool


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
        user = await uow.users.get_for_update(user_id)
        if user is None:
            raise SignalRuleError("User not found")
        overview = await self.overview(uow, user=user)
        if overview.access.is_blocked:
            raise SignalRuleError("Access is blocked")
        if not overview.is_registered:
            raise SignalRuleError("Broker registration is required")
        if not overview.has_deposit:
            raise SignalRuleError("A deposit is required")
        if timeframe_seconds not in allowed_timeframes(overview.access.status_policy):
            raise SignalRuleError("Timeframe is not available")
        now = self._clock.now()
        availability = overview.premium if premium else overview.standard
        if availability.limit is not None and availability.used >= availability.limit:
            raise SignalRuleError("Daily signal limit reached")
        if availability.next_available_at and availability.next_available_at > now:
            raise SignalRuleError("Signal wait is active")
        asset = await uow.signals.get_active_asset(asset_id)
        if asset is None:
            raise SignalRuleError("Signal asset is unavailable")
        if premium and not overview.is_premium_available:
            raise SignalRuleError("Premium signal requires a larger deposit")
        signal = await uow.signals.add(
            user_id=user_id,
            asset=asset,
            timeframe_seconds=timeframe_seconds,
            direction=self._randomizer.direction().value,
            probability=self._randomizer.probability(
                overview.access.status_policy, premium=premium
            ),
            premium=premium,
            requested_at=now,
        )
        await uow.engagement.add_activity(
            user_id=user.id,
            activity_type=ActivityType.SIGNAL_GENERATED.value,
            occurred_at=now,
        )
        return signal

    async def overview(self, uow: UnitOfWork, *, user: User) -> UserSignalOverview:
        access = await self._access_service.snapshot(uow, user=user)
        settings = await uow.settings.get_or_create()
        standard = await self.availability(
            uow,
            user_id=user.id,
            premium=False,
            daily_limit=access.status_policy.daily_signal_limit,
            wait_seconds=access.status_policy.signal_wait_seconds,
        )
        premium = await self.availability(
            uow,
            user_id=user.id,
            premium=True,
            daily_limit=settings.premium_daily_limit,
            wait_seconds=5,
        )
        return UserSignalOverview(
            access=access,
            is_registered=await uow.finance.has_account(user.id),
            has_deposit=access.total_deposits > 0,
            standard=standard,
            premium=premium,
            premium_minimum_deposit=settings.premium_minimum_deposit,
            is_premium_available=(
                access.total_deposits >= settings.premium_minimum_deposit
            ),
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
