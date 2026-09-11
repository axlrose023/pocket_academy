import datetime
import uuid
from dataclasses import dataclass
from decimal import Decimal

from sqlalchemy import and_, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import BrokerAccount, Deposit, Withdrawal


@dataclass(frozen=True, slots=True)
class WithdrawalUpsertResult:
    withdrawal: Withdrawal
    was_applied: bool


@dataclass(frozen=True, slots=True)
class WithdrawalCoverage:
    withdrawal: Withdrawal
    deposits_after: Decimal


class FinanceDAO:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def total_deposits(self, user_id: uuid.UUID) -> Decimal:
        amount = await self._session.scalar(
            select(func.coalesce(func.sum(Deposit.amount), 0)).where(
                Deposit.user_id == user_id,
            )
        )
        return Decimal(amount)

    async def get_account(
        self, *, provider: str, trader_id: str
    ) -> BrokerAccount | None:
        return await self._session.scalar(
            select(BrokerAccount).where(
                BrokerAccount.provider == provider,
                BrokerAccount.trader_id == trader_id,
            )
        )

    async def has_account(self, user_id: uuid.UUID) -> bool:
        return (
            await self._session.scalar(
                select(BrokerAccount.id).where(BrokerAccount.user_id == user_id)
            )
            is not None
        )

    async def first_deposit(self, user_id: uuid.UUID) -> Deposit | None:
        return await self._session.scalar(
            select(Deposit)
            .where(Deposit.user_id == user_id)
            .order_by(Deposit.occurred_at, Deposit.created_at)
            .limit(1)
        )

    async def list_recent_deposits(
        self, *, user_id: uuid.UUID, limit: int
    ) -> list[Deposit]:
        return list(
            (
                await self._session.scalars(
                    select(Deposit)
                    .where(Deposit.user_id == user_id)
                    .order_by(Deposit.occurred_at.desc())
                    .limit(limit)
                )
            ).all()
        )

    async def create_account(
        self,
        *,
        user_id: uuid.UUID,
        attribution_click_id: uuid.UUID | None,
        provider: str,
        trader_id: str,
        registered_at: datetime.datetime,
    ) -> BrokerAccount:
        account = BrokerAccount(
            user_id=user_id,
            attribution_click_id=attribution_click_id,
            provider=provider,
            trader_id=trader_id,
            registered_at=registered_at,
        )
        self._session.add(account)
        return account

    async def unresolved_withdrawal_coverages(
        self, user_id: uuid.UUID
    ) -> list[WithdrawalCoverage]:
        rows = await self._session.execute(
            select(
                Withdrawal,
                func.coalesce(func.sum(Deposit.amount), 0).label("deposits_after"),
            )
            .outerjoin(
                Deposit,
                and_(
                    Deposit.user_id == Withdrawal.user_id,
                    Deposit.occurred_at >= Withdrawal.requested_at,
                ),
            )
            .where(
                Withdrawal.user_id == user_id,
                Withdrawal.status.in_(("new", "success")),
            )
            .group_by(Withdrawal.id)
        )
        return [
            WithdrawalCoverage(withdrawal=withdrawal, deposits_after=Decimal(amount))
            for withdrawal, amount in rows
        ]

    async def add_deposit(
        self,
        *,
        user_id: uuid.UUID,
        broker_account_id: uuid.UUID,
        external_event_id: uuid.UUID,
        kind: str,
        amount: Decimal,
        occurred_at: datetime.datetime,
    ) -> Deposit:
        deposit = Deposit(
            user_id=user_id,
            broker_account_id=broker_account_id,
            external_event_id=external_event_id,
            kind=kind,
            amount=amount,
            occurred_at=occurred_at,
        )
        self._session.add(deposit)
        return deposit

    async def upsert_withdrawal(
        self,
        *,
        user_id: uuid.UUID,
        broker_account_id: uuid.UUID,
        external_event_id: uuid.UUID,
        provider: str,
        external_reference: str,
        amount: Decimal,
        status: str,
        occurred_at: datetime.datetime,
        resolved_at: datetime.datetime | None,
    ) -> WithdrawalUpsertResult:
        withdrawal = await self._session.scalar(
            select(Withdrawal).where(
                Withdrawal.provider == provider,
                Withdrawal.external_reference == external_reference,
            )
        )
        if withdrawal is None:
            withdrawal = Withdrawal(
                user_id=user_id,
                broker_account_id=broker_account_id,
                provider=provider,
                external_reference=external_reference,
                amount=amount,
                status=status,
                requested_at=occurred_at,
                last_external_event_id=external_event_id,
                resolved_at=resolved_at,
            )
            self._session.add(withdrawal)
            return WithdrawalUpsertResult(withdrawal=withdrawal, was_applied=True)
        earliest_requested_at = min(withdrawal.requested_at, occurred_at)
        withdrawal.requested_at = earliest_requested_at
        current_status_rank = _withdrawal_status_rank(withdrawal.status)
        received_status_rank = _withdrawal_status_rank(status)
        if received_status_rank < current_status_rank:
            return WithdrawalUpsertResult(withdrawal=withdrawal, was_applied=False)
        if received_status_rank == current_status_rank:
            if status == withdrawal.status:
                return WithdrawalUpsertResult(withdrawal=withdrawal, was_applied=False)
            current_status_at = withdrawal.resolved_at or earliest_requested_at
            if occurred_at <= current_status_at:
                return WithdrawalUpsertResult(withdrawal=withdrawal, was_applied=False)
        withdrawal.last_external_event_id = external_event_id
        withdrawal.amount = amount
        withdrawal.status = status
        withdrawal.resolved_at = resolved_at
        return WithdrawalUpsertResult(withdrawal=withdrawal, was_applied=True)


def _withdrawal_status_rank(status: str) -> int:
    return {"new": 0, "cancelled": 1, "success": 1}.get(status, -1)
