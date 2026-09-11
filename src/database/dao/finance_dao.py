import datetime
import uuid
from decimal import Decimal

from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import BrokerAccount, Deposit, Withdrawal


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

    async def deposits_after(
        self, user_id: uuid.UUID, occurred_at: datetime.datetime
    ) -> Decimal:
        amount = await self._session.scalar(
            select(func.coalesce(func.sum(Deposit.amount), 0)).where(
                Deposit.user_id == user_id,
                Deposit.occurred_at >= occurred_at,
            )
        )
        return Decimal(amount)

    async def unresolved_withdrawals(self, user_id: uuid.UUID) -> list[Withdrawal]:
        return list(
            (
                await self._session.scalars(
                    select(Withdrawal).where(
                        Withdrawal.user_id == user_id,
                        Withdrawal.status.in_(("new", "success")),
                    )
                )
            ).all()
        )

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
        requested_at: datetime.datetime,
        resolved_at: datetime.datetime | None,
    ) -> Withdrawal:
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
                requested_at=requested_at,
            )
            self._session.add(withdrawal)
        withdrawal.last_external_event_id = external_event_id
        withdrawal.amount = amount
        withdrawal.status = status
        withdrawal.resolved_at = resolved_at
        return withdrawal
