import datetime
from dataclasses import dataclass
from decimal import Decimal

from database.models import ExternalEvent, User
from database.uow import UnitOfWork
from domain.enums import DepositKind, PacEntryReason
from services.products import ProductService


class BrokerEventError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class BrokerRegistration:
    click_id: str
    trader_id: str
    occurred_at: datetime.datetime


@dataclass(frozen=True, slots=True)
class BrokerDeposit:
    trader_id: str
    amount: Decimal
    kind: DepositKind
    occurred_at: datetime.datetime


class BrokerEventService:
    def __init__(self, product_service: ProductService) -> None:
        self._product_service = product_service

    async def register(
        self, uow: UnitOfWork, *, event: ExternalEvent, registration: BrokerRegistration
    ) -> User:
        attribution = await uow.attribution.get_by_click_id(registration.click_id)
        if attribution is None:
            raise BrokerEventError("Unknown attribution click")
        user = await uow.users.ensure_telegram_id(attribution.telegram_id)
        account = await uow.finance.get_account(
            provider=event.provider, trader_id=registration.trader_id
        )
        if account is None:
            await uow.finance.create_account(
                user_id=user.id,
                attribution_click_id=attribution.id,
                provider=event.provider,
                trader_id=registration.trader_id,
                registered_at=registration.occurred_at,
            )
        await self._product_service.grant_automatic(
            uow, user_id=user.id, registered=True, total_deposits=Decimal("0")
        )
        await uow.external_events.mark_processed(event)
        return user

    async def deposit(
        self, uow: UnitOfWork, *, event: ExternalEvent, deposit: BrokerDeposit
    ) -> None:
        account = await uow.finance.get_account(
            provider=event.provider, trader_id=deposit.trader_id
        )
        if account is None:
            raise BrokerEventError("Unknown broker account")
        await uow.finance.add_deposit(
            user_id=account.user_id,
            broker_account_id=account.id,
            external_event_id=event.id,
            kind=deposit.kind.value,
            amount=deposit.amount,
            occurred_at=deposit.occurred_at,
        )
        await uow.pac_ledger.add(
            user_id=account.user_id,
            amount=deposit.amount,
            reason=PacEntryReason.DEPOSIT.value,
            reference_id=event.id,
            note=f"{deposit.kind.value.title()} deposit",
        )
        total_deposits = await uow.finance.total_deposits(account.user_id)
        await self._product_service.grant_automatic(
            uow,
            user_id=account.user_id,
            registered=False,
            total_deposits=total_deposits,
        )
        await uow.engagement.add_notification(
            user_id=account.user_id,
            notification_type="deposit",
            title="PAC credited",
            body=f"Deposit: ${deposit.amount}. {deposit.amount} PAC added.",
        )
        await uow.external_events.mark_processed(event)
