import datetime
from dataclasses import dataclass
from decimal import Decimal
from typing import TypeVar

from database.models import ExternalEvent, User
from database.uow import UnitOfWork
from domain.clock import Clock
from domain.enums import (
    DepositKind,
    ExternalEventType,
    PacEntryReason,
    WithdrawalStatus,
)
from services.external_events import PocketOptionEventParser, PocketOptionPostback
from services.products import ProductService


class BrokerEventError(ValueError):
    pass


ValueT = TypeVar("ValueT")


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


@dataclass(frozen=True, slots=True)
class BrokerWithdrawal:
    trader_id: str
    external_reference: str
    amount: Decimal
    status: WithdrawalStatus
    occurred_at: datetime.datetime


class BrokerEventService:
    def __init__(self, product_service: ProductService, clock: Clock) -> None:
        self._product_service = product_service
        self._clock = clock

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
        await uow.external_events.mark_processed(
            event,
            processed_at=self._clock.now(),
        )
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
        await uow.external_events.mark_processed(
            event,
            processed_at=self._clock.now(),
        )

    async def withdrawal(
        self,
        uow: UnitOfWork,
        *,
        event: ExternalEvent,
        withdrawal: BrokerWithdrawal,
    ) -> None:
        account = await uow.finance.get_account(
            provider=event.provider,
            trader_id=withdrawal.trader_id,
        )
        if account is None:
            raise BrokerEventError("Unknown broker account")
        await uow.finance.upsert_withdrawal(
            user_id=account.user_id,
            broker_account_id=account.id,
            external_event_id=event.id,
            provider=event.provider,
            external_reference=withdrawal.external_reference,
            amount=withdrawal.amount,
            status=withdrawal.status.value,
            requested_at=withdrawal.occurred_at,
            resolved_at=(
                withdrawal.occurred_at
                if withdrawal.status != WithdrawalStatus.NEW
                else None
            ),
        )
        await uow.external_events.mark_processed(
            event,
            processed_at=self._clock.now(),
        )


class PocketOptionEventService:
    def __init__(
        self,
        broker_event_service: BrokerEventService,
        parser: PocketOptionEventParser,
    ) -> None:
        self._broker_event_service = broker_event_service
        self._parser = parser

    async def process(
        self,
        uow: UnitOfWork,
        *,
        event: ExternalEvent,
        postback: PocketOptionPostback,
    ) -> bool:
        if event.processing_status == "processed":
            return True
        try:
            await self._process_once(uow, event=event, postback=postback)
        except BrokerEventError:
            return False
        if postback.event_type == ExternalEventType.REGISTRATION:
            await self.retry_pending_for_trader(uow, trader_id=postback.trader_id)
        return True

    async def retry_pending_for_trader(
        self, uow: UnitOfWork, *, trader_id: str | None
    ) -> None:
        if trader_id is None:
            return
        events = await uow.external_events.list_received_pocket_option_events(
            trader_id=trader_id
        )
        for event in events:
            postback = self._parse_normalized(event)
            if (
                postback is None
                or postback.event_type == ExternalEventType.REGISTRATION
            ):
                continue
            try:
                await self._process_once(uow, event=event, postback=postback)
            except BrokerEventError:
                continue

    async def retry_pending_for_click_id(
        self, uow: UnitOfWork, *, click_id: str
    ) -> None:
        events = await uow.external_events.list_received_pocket_option_events(
            click_id=click_id
        )
        for event in events:
            postback = self._parse_normalized(event)
            if (
                postback is None
                or postback.event_type != ExternalEventType.REGISTRATION
            ):
                continue
            await self.process(uow, event=event, postback=postback)

    async def _process_once(
        self,
        uow: UnitOfWork,
        *,
        event: ExternalEvent,
        postback: PocketOptionPostback,
    ) -> None:
        if postback.event_type == ExternalEventType.REGISTRATION:
            await self._broker_event_service.register(
                uow,
                event=event,
                registration=BrokerRegistration(
                    click_id=_required(postback.click_id),
                    trader_id=_required(postback.trader_id),
                    occurred_at=postback.occurred_at,
                ),
            )
            return
        if postback.event_type in (
            ExternalEventType.FIRST_DEPOSIT,
            ExternalEventType.REPEAT_DEPOSIT,
        ):
            await self._broker_event_service.deposit(
                uow,
                event=event,
                deposit=BrokerDeposit(
                    trader_id=_required(postback.trader_id),
                    amount=_required(postback.amount),
                    kind=(
                        DepositKind.FIRST
                        if postback.event_type == ExternalEventType.FIRST_DEPOSIT
                        else DepositKind.REPEAT
                    ),
                    occurred_at=postback.occurred_at,
                ),
            )
            return
        if postback.event_type == ExternalEventType.WITHDRAWAL:
            await self._broker_event_service.withdrawal(
                uow,
                event=event,
                withdrawal=BrokerWithdrawal(
                    trader_id=_required(postback.trader_id),
                    external_reference=_required(postback.withdrawal_reference),
                    amount=_required(postback.amount),
                    status=_required(postback.withdrawal_status),
                    occurred_at=postback.occurred_at,
                ),
            )
            return
        raise BrokerEventError("Unsupported broker event")

    def _parse_normalized(self, event: ExternalEvent) -> PocketOptionPostback | None:
        normalized = event.payload.get("_normalized")
        if not isinstance(normalized, dict):
            return None
        return self._parser.parse(normalized)


def _required(value: ValueT | None) -> ValueT:
    if value is None:
        raise BrokerEventError("Missing normalized postback value")
    return value
