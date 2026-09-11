import datetime
import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import (
    AuditLog,
    BrokerAccount,
    Deposit,
    DiaryEntry,
    Product,
    Signal,
    SignalAsset,
    User,
)


@dataclass(frozen=True, slots=True)
class AdminDashboardTotals:
    registrations: int
    first_deposits: int
    first_deposit_amount: Decimal
    repeat_deposits: int
    repeat_deposit_amount: Decimal
    signals: int
    diary_entries: int
    active_users: int


class AdminDAO:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_user(self, identifier: str) -> User | None:
        if identifier.isdigit():
            return await self._session.scalar(
                select(User).where(User.telegram_id == int(identifier))
            )
        return await self._session.scalar(
            select(User).where(User.username == identifier.lstrip("@"))
        )

    async def set_user_blocked(
        self, user: User, *, blocked: bool, reason: str | None
    ) -> None:
        user.is_manually_blocked = blocked
        user.is_manually_unblocked = not blocked
        user.manual_block_reason = reason if blocked else None

    async def get_product(self, product_id: uuid.UUID) -> Product | None:
        return await self._session.get(Product, product_id)

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
    ) -> AdminDashboardTotals:
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
            registrations=registrations,
            first_deposits=int(deposit_row[0] or 0),
            first_deposit_amount=Decimal(deposit_row[1]),
            repeat_deposits=int(deposit_row[2] or 0),
            repeat_deposit_amount=Decimal(deposit_row[3]),
            signals=signals,
            diary_entries=diary_entries,
            active_users=active_users,
        )
