import datetime
import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import Date, cast, func, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    AttributionClick,
    AuditLog,
    BrokerAccount,
    Deposit,
    DiaryEntry,
    Product,
    ProductMaterial,
    Signal,
    SignalAsset,
    User,
)


@dataclass(frozen=True, slots=True)
class AdminDashboardTotals:
    leads: int
    registrations: int
    first_deposits: int
    first_deposit_amount: Decimal
    repeat_deposits: int
    repeat_deposit_amount: Decimal
    signals: int
    diary_entries: int
    active_users: int
    diary_statistics: "AdminDiaryStatistics"
    series: tuple["AdminDashboardSeriesPoint", ...]


@dataclass(frozen=True, slots=True)
class AdminDiaryStatistics:
    profitable_trades: int
    losing_trades: int
    average_mood: Decimal | None
    mood_distribution: tuple[int, int, int, int, int]


@dataclass(frozen=True, slots=True)
class AdminDashboardSeriesPoint:
    period_start: datetime.date
    leads: int
    registrations: int
    first_deposits: int
    first_deposit_amount: Decimal
    repeat_deposits: int
    repeat_deposit_amount: Decimal
    signals: int
    diary_entries: int


class AdminDAO:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_user(self, identifier: str) -> User | None:
        normalized_identifier = identifier.strip()
        username = normalized_identifier.lstrip("@")
        conditions = [
            User.username == username,
            AttributionClick.click_id == normalized_identifier,
            AttributionClick.link_chat == normalized_identifier,
            BrokerAccount.trader_id == normalized_identifier,
        ]
        if normalized_identifier.isdigit():
            conditions.append(User.telegram_id == int(normalized_identifier))
        return await self._session.scalar(
            select(User)
            .outerjoin(
                AttributionClick,
                AttributionClick.telegram_id == User.telegram_id,
            )
            .outerjoin(BrokerAccount, BrokerAccount.user_id == User.id)
            .where(or_(*conditions))
            .order_by(User.telegram_id)
        )

    async def user_trader_ids(self, user_id: uuid.UUID) -> list[str]:
        return list(
            (
                await self._session.scalars(
                    select(BrokerAccount.trader_id)
                    .where(BrokerAccount.user_id == user_id)
                    .order_by(BrokerAccount.registered_at.desc())
                )
            ).all()
        )

    async def latest_attribution(self, telegram_id: int) -> AttributionClick | None:
        return await self._session.scalar(
            select(AttributionClick)
            .where(AttributionClick.telegram_id == telegram_id)
            .order_by(AttributionClick.recorded_at.desc())
        )

    async def set_user_blocked(
        self, user: User, *, blocked: bool, reason: str | None
    ) -> None:
        user.is_manually_blocked = blocked
        user.is_manually_unblocked = not blocked
        user.manual_block_reason = reason if blocked else None

    async def get_product(self, product_id: uuid.UUID) -> Product | None:
        return await self._session.get(Product, product_id)

    async def get_material(self, material_id: uuid.UUID) -> ProductMaterial | None:
        return await self._session.get(ProductMaterial, material_id)

    async def list_materials(self, product_id: uuid.UUID) -> list[ProductMaterial]:
        return list(
            (
                await self._session.scalars(
                    select(ProductMaterial)
                    .where(ProductMaterial.product_id == product_id)
                    .order_by(ProductMaterial.sort_order, ProductMaterial.created_at)
                )
            ).all()
        )

    async def list_products(self) -> list[Product]:
        return list(
            (
                await self._session.scalars(
                    select(Product).order_by(Product.sort_order)
                )
            ).all()
        )

    async def get_asset(self, asset_id: uuid.UUID) -> SignalAsset | None:
        return await self._session.get(SignalAsset, asset_id)

    async def get_asset_by_key(self, asset_key: str) -> SignalAsset | None:
        return await self._session.scalar(
            select(SignalAsset).where(SignalAsset.asset_key == asset_key)
        )

    async def list_assets(self) -> list[SignalAsset]:
        return list(
            (
                await self._session.scalars(
                    select(SignalAsset).order_by(SignalAsset.sort_order)
                )
            ).all()
        )

    async def add_audit_log(
        self,
        *,
        actor_id: uuid.UUID,
        action: str,
        payload: dict,
        target_user_id: uuid.UUID | None = None,
    ) -> AuditLog:
        audit_log = AuditLog(
            actor_id=actor_id,
            target_user_id=target_user_id,
            action=action,
            payload=payload,
        )
        self._session.add(audit_log)
        return audit_log

    async def dashboard_totals(
        self,
        *,
        occurred_from: datetime.datetime,
        occurred_until: datetime.datetime,
        day_from: datetime.date,
        day_until: datetime.date,
        granularity: str,
    ) -> AdminDashboardTotals:
        leads = int(
            await self._session.scalar(
                select(func.count()).where(
                    AttributionClick.recorded_at >= occurred_from,
                    AttributionClick.recorded_at < occurred_until,
                )
            )
            or 0
        )
        registrations = int(
            await self._session.scalar(
                select(func.count()).where(
                    BrokerAccount.registered_at >= occurred_from,
                    BrokerAccount.registered_at < occurred_until,
                )
            )
            or 0
        )
        deposit_row = (
            await self._session.execute(
                select(
                    func.count().filter(Deposit.kind == "first"),
                    func.coalesce(
                        func.sum(Deposit.amount).filter(Deposit.kind == "first"),
                        0,
                    ),
                    func.count().filter(Deposit.kind == "repeat"),
                    func.coalesce(
                        func.sum(Deposit.amount).filter(Deposit.kind == "repeat"),
                        0,
                    ),
                ).where(
                    Deposit.occurred_at >= occurred_from,
                    Deposit.occurred_at < occurred_until,
                )
            )
        ).one()
        signals = int(
            await self._session.scalar(
                select(func.count()).where(
                    Signal.requested_at >= occurred_from,
                    Signal.requested_at < occurred_until,
                )
            )
            or 0
        )
        diary_entries = int(
            await self._session.scalar(
                select(func.count()).where(
                    DiaryEntry.entry_day >= day_from,
                    DiaryEntry.entry_day <= day_until,
                )
            )
            or 0
        )
        diary_row = (
            await self._session.execute(
                select(
                    func.coalesce(func.sum(DiaryEntry.profitable_trades), 0),
                    func.coalesce(func.sum(DiaryEntry.losing_trades), 0),
                    func.avg(DiaryEntry.mood),
                    *[
                        func.count().filter(DiaryEntry.mood == mood)
                        for mood in range(1, 6)
                    ],
                ).where(
                    DiaryEntry.entry_day >= day_from,
                    DiaryEntry.entry_day <= day_until,
                )
            )
        ).one()
        active_users = int(
            await self._session.scalar(
                select(func.count()).where(
                    User.last_seen_at >= occurred_from,
                    User.last_seen_at < occurred_until,
                )
            )
            or 0
        )
        return AdminDashboardTotals(
            leads=leads,
            registrations=registrations,
            first_deposits=int(deposit_row[0] or 0),
            first_deposit_amount=Decimal(deposit_row[1]),
            repeat_deposits=int(deposit_row[2] or 0),
            repeat_deposit_amount=Decimal(deposit_row[3]),
            signals=signals,
            diary_entries=diary_entries,
            active_users=active_users,
            diary_statistics=AdminDiaryStatistics(
                profitable_trades=int(diary_row[0] or 0),
                losing_trades=int(diary_row[1] or 0),
                average_mood=(
                    Decimal(diary_row[2]) if diary_row[2] is not None else None
                ),
                mood_distribution=tuple(int(value or 0) for value in diary_row[3:]),
            ),
            series=tuple(
                await self._dashboard_series(
                    occurred_from=occurred_from,
                    occurred_until=occurred_until,
                    day_from=day_from,
                    day_until=day_until,
                    granularity=granularity,
                )
            ),
        )

    async def _dashboard_series(
        self,
        *,
        occurred_from: datetime.datetime,
        occurred_until: datetime.datetime,
        day_from: datetime.date,
        day_until: datetime.date,
        granularity: str,
    ) -> list[AdminDashboardSeriesPoint]:
        periods = {
            period_start: {
                "leads": 0,
                "registrations": 0,
                "first_deposits": 0,
                "first_deposit_amount": Decimal("0"),
                "repeat_deposits": 0,
                "repeat_deposit_amount": Decimal("0"),
                "signals": 0,
                "diary_entries": 0,
            }
            for period_start in _period_starts(day_from, day_until, granularity)
        }
        for period_start, count in await self._time_series_counts(
            AttributionClick.recorded_at,
            AttributionClick,
            occurred_from=occurred_from,
            occurred_until=occurred_until,
            granularity=granularity,
        ):
            periods[period_start]["leads"] = count
        for period_start, count in await self._time_series_counts(
            BrokerAccount.registered_at,
            BrokerAccount,
            occurred_from=occurred_from,
            occurred_until=occurred_until,
            granularity=granularity,
        ):
            periods[period_start]["registrations"] = count
        for (
            period_start,
            first_count,
            first_amount,
            repeat_count,
            repeat_amount,
        ) in await self._deposit_series(
            occurred_from=occurred_from,
            occurred_until=occurred_until,
            granularity=granularity,
        ):
            period = periods[period_start]
            period["first_deposits"] = first_count
            period["first_deposit_amount"] = first_amount
            period["repeat_deposits"] = repeat_count
            period["repeat_deposit_amount"] = repeat_amount
        for period_start, count in await self._time_series_counts(
            Signal.requested_at,
            Signal,
            occurred_from=occurred_from,
            occurred_until=occurred_until,
            granularity=granularity,
        ):
            periods[period_start]["signals"] = count
        for period_start, count in await self._diary_series(
            day_from=day_from,
            day_until=day_until,
            granularity=granularity,
        ):
            periods[period_start]["diary_entries"] = count
        return [
            AdminDashboardSeriesPoint(period_start=period_start, **metrics)
            for period_start, metrics in periods.items()
        ]

    async def _time_series_counts(
        self,
        timestamp_column,
        model,
        *,
        occurred_from: datetime.datetime,
        occurred_until: datetime.datetime,
        granularity: str,
    ) -> list[tuple[datetime.date, int]]:
        period = _utc_period(timestamp_column, granularity)
        rows = await self._session.execute(
            select(period, func.count())
            .select_from(model)
            .where(timestamp_column >= occurred_from, timestamp_column < occurred_until)
            .group_by(period)
            .order_by(period)
        )
        return [(period_start, int(count)) for period_start, count in rows]

    async def _deposit_series(
        self,
        *,
        occurred_from: datetime.datetime,
        occurred_until: datetime.datetime,
        granularity: str,
    ) -> list[tuple[datetime.date, int, Decimal, int, Decimal]]:
        period = _utc_period(Deposit.occurred_at, granularity)
        rows = await self._session.execute(
            select(
                period,
                func.count().filter(Deposit.kind == "first"),
                func.coalesce(
                    func.sum(Deposit.amount).filter(Deposit.kind == "first"), 0
                ),
                func.count().filter(Deposit.kind == "repeat"),
                func.coalesce(
                    func.sum(Deposit.amount).filter(Deposit.kind == "repeat"), 0
                ),
            )
            .where(
                Deposit.occurred_at >= occurred_from,
                Deposit.occurred_at < occurred_until,
            )
            .group_by(period)
            .order_by(period)
        )
        return [
            (
                period_start,
                int(first_count or 0),
                Decimal(first_amount or 0),
                int(repeat_count or 0),
                Decimal(repeat_amount or 0),
            )
            for period_start, first_count, first_amount, repeat_count, repeat_amount in rows
        ]

    async def _diary_series(
        self,
        *,
        day_from: datetime.date,
        day_until: datetime.date,
        granularity: str,
    ) -> list[tuple[datetime.date, int]]:
        period = _date_period(DiaryEntry.entry_day, granularity)
        rows = await self._session.execute(
            select(period, func.count())
            .where(DiaryEntry.entry_day >= day_from, DiaryEntry.entry_day <= day_until)
            .group_by(period)
            .order_by(period)
        )
        return [(period_start, int(count)) for period_start, count in rows]


def _utc_period(timestamp_column, granularity: str):
    return cast(
        func.date_trunc(granularity, func.timezone("UTC", timestamp_column)),
        Date,
    ).label("period_start")


def _date_period(day_column, granularity: str):
    if granularity == "day":
        return day_column.label("period_start")
    return cast(func.date_trunc(granularity, day_column), Date).label("period_start")


def _period_starts(
    day_from: datetime.date,
    day_until: datetime.date,
    granularity: str,
) -> list[datetime.date]:
    period_start = _period_start(day_from, granularity)
    periods: list[datetime.date] = []
    while period_start <= day_until:
        periods.append(period_start)
        period_start = _next_period_start(period_start, granularity)
    return periods


def _period_start(day: datetime.date, granularity: str) -> datetime.date:
    if granularity == "day":
        return day
    if granularity == "week":
        return day - datetime.timedelta(days=day.weekday())
    return day.replace(day=1)


def _next_period_start(day: datetime.date, granularity: str) -> datetime.date:
    if granularity == "day":
        return day + datetime.timedelta(days=1)
    if granularity == "week":
        return day + datetime.timedelta(days=7)
    return (day.replace(day=28) + datetime.timedelta(days=4)).replace(day=1)
