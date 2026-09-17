import datetime
import hashlib
import json
from dataclasses import dataclass
from decimal import Decimal, InvalidOperation
from typing import Any

from database.models import ExternalEvent
from database.uow import UnitOfWork
from domain.clock import Clock
from domain.enums import ExternalEventType, ExternalProvider, WithdrawalStatus
from services.exceptions import UnsupportedExternalEventError


class ExternalEventService:
    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    async def record(
        self,
        uow: UnitOfWork,
        *,
        provider: ExternalProvider,
        event_type: ExternalEventType,
        payload: dict[str, Any],
        source_event_id: str | None,
        occurred_at: datetime.datetime | None = None,
        normalized_payload: dict[str, Any] | None = None,
        deduplication_identity: str | None = None,
    ) -> tuple[ExternalEvent, bool]:
        canonical_payload = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            default=str,
        )
        identity = deduplication_identity or source_event_id or canonical_payload
        deduplication_key = hashlib.sha256(
            f"{provider.value}:{event_type.value}:{identity}".encode()
        ).hexdigest()
        return await uow.external_events.create_or_get(
            provider=provider.value,
            event_type=event_type.value,
            deduplication_key=deduplication_key,
            source_event_id=source_event_id,
            payload=(
                {**payload, "_normalized": normalized_payload}
                if normalized_payload is not None
                else payload
            ),
            occurred_at=occurred_at,
            received_at=self._clock.now(),
        )

    async def record_rejected(
        self,
        uow: UnitOfWork,
        *,
        provider: ExternalProvider,
        payload: dict[str, Any],
        reason: str,
    ) -> bool:
        event, created = await self.record(
            uow,
            provider=provider,
            event_type=ExternalEventType.UNKNOWN,
            payload=payload,
            source_event_id=None,
        )
        await uow.external_events.mark_rejected(
            event,
            rejected_at=self._clock.now(),
            reason=reason,
        )
        return created


class PocketOptionEventParser:
    _event_types = {
        "registration": ExternalEventType.REGISTRATION,
        "reg": ExternalEventType.REGISTRATION,
        "fd": ExternalEventType.FIRST_DEPOSIT,
        "ftd": ExternalEventType.FIRST_DEPOSIT,
        "sale": ExternalEventType.FIRST_DEPOSIT,
        "first_deposit": ExternalEventType.FIRST_DEPOSIT,
        "rd": ExternalEventType.REPEAT_DEPOSIT,
        "resale": ExternalEventType.REPEAT_DEPOSIT,
        "repeat_deposit": ExternalEventType.REPEAT_DEPOSIT,
        "withdrawal": ExternalEventType.WITHDRAWAL,
    }
    _event_keys = ("event_type", "event", "tracker.event", "goal")
    _event_id_keys = (
        "event_id",
        "transaction_id",
        "tid",
        "withdrawal_id",
        "deposit_id",
        "order_id",
    )
    _click_id_keys = ("click_id", "clickid", "sub_id", "sub_id1")
    _trader_id_keys = ("trader_id", "playerid", "player_id", "user_id")
    _amount_keys = ("amount", "sum", "sumdep", "revenue", "value")
    _occurred_at_keys = ("occurred_at", "event_time", "timestamp", "created_at")
    _currency_keys = ("currency", "cur")
    _withdrawal_statuses = {
        "new": WithdrawalStatus.NEW,
        "pending": WithdrawalStatus.NEW,
        "cancelled": WithdrawalStatus.CANCELLED,
        "canceled": WithdrawalStatus.CANCELLED,
        "rejected": WithdrawalStatus.CANCELLED,
        "success": WithdrawalStatus.SUCCESS,
        "approved": WithdrawalStatus.SUCCESS,
        "completed": WithdrawalStatus.SUCCESS,
        "paid": WithdrawalStatus.SUCCESS,
    }

    def __init__(self, clock: Clock) -> None:
        self._clock = clock

    def parse(self, payload: dict[str, Any]) -> "PocketOptionPostback":
        raw_event_type = (self._first_text(payload, self._event_keys) or "").lower()
        event_type = self._event_types.get(raw_event_type)
        if event_type is None:
            raise UnsupportedExternalEventError("Unsupported Pocket Option event type")
        source_event_id = self._first_text(payload, self._event_id_keys)
        click_id = self._first_text(payload, self._click_id_keys)
        trader_id = self._first_text(payload, self._trader_id_keys)
        occurred_at = self._parse_occurred_at(
            self._first(payload, self._occurred_at_keys)
        )
        currency = self._first_text(payload, self._currency_keys)
        if currency is not None and currency.lower() != "usd":
            raise UnsupportedExternalEventError("Pocket Option currency must be USD")

        amount = None
        if event_type != ExternalEventType.REGISTRATION:
            amount = self._parse_amount(self._first(payload, self._amount_keys))
        if event_type == ExternalEventType.REGISTRATION:
            self._require(click_id, "click_id")
            self._require(trader_id, "trader_id")
        else:
            self._require(trader_id, "trader_id")
        withdrawal_status = None
        if event_type == ExternalEventType.WITHDRAWAL:
            self._require(source_event_id, "event_id")
            raw_status = self._first_text(payload, ("withdrawal_status", "status"))
            withdrawal_status = self._withdrawal_statuses.get(
                (raw_status or "").lower()
            )
            if withdrawal_status is None:
                raise UnsupportedExternalEventError("Unsupported withdrawal status")
        withdrawal_reference = (
            self._first_text(
                payload,
                ("withdrawal_id", "withdrawal_reference", "transaction_id", "tid"),
            )
            or source_event_id
        )
        return PocketOptionPostback(
            event_type=event_type,
            source_event_id=source_event_id,
            click_id=click_id,
            trader_id=trader_id,
            amount=amount,
            occurred_at=occurred_at,
            withdrawal_status=withdrawal_status,
            withdrawal_reference=withdrawal_reference,
        )

    @staticmethod
    def _first(payload: dict[str, Any], keys: tuple[str, ...]) -> Any:
        return next(
            (payload[key] for key in keys if payload.get(key) is not None), None
        )

    @classmethod
    def _first_text(cls, payload: dict[str, Any], keys: tuple[str, ...]) -> str | None:
        value = cls._first(payload, keys)
        if value is None:
            return None
        text = str(value).strip()
        return text or None

    def _parse_occurred_at(self, value: Any) -> datetime.datetime:
        if value is None:
            return self._clock.now()
        if isinstance(value, (int, float)) or (
            isinstance(value, str) and value.replace(".", "", 1).isdigit()
        ):
            timestamp = float(value)
            if timestamp > 10_000_000_000:
                timestamp /= 1_000
            return datetime.datetime.fromtimestamp(timestamp, tz=datetime.UTC)
        try:
            parsed = datetime.datetime.fromisoformat(str(value).replace("Z", "+00:00"))
        except ValueError as error:
            raise UnsupportedExternalEventError("Invalid event timestamp") from error
        return (
            parsed.replace(tzinfo=datetime.UTC)
            if parsed.tzinfo is None
            else parsed.astimezone(datetime.UTC)
        )

    @staticmethod
    def _parse_amount(value: Any) -> Decimal:
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, TypeError) as error:
            raise UnsupportedExternalEventError("Invalid event amount") from error
        if amount <= 0:
            raise UnsupportedExternalEventError("Event amount must be positive")
        return amount

    @staticmethod
    def _require(value: str | None, field_name: str) -> None:
        if value is None:
            raise UnsupportedExternalEventError(f"Missing {field_name}")


@dataclass(frozen=True, slots=True)
class PocketOptionPostback:
    event_type: ExternalEventType
    source_event_id: str | None
    click_id: str | None
    trader_id: str | None
    amount: Decimal | None
    occurred_at: datetime.datetime
    withdrawal_status: WithdrawalStatus | None
    withdrawal_reference: str | None

    @property
    def deduplication_identity(self) -> str | None:
        if self.event_type != ExternalEventType.WITHDRAWAL:
            return self.source_event_id
        if self.source_event_id is None or self.withdrawal_status is None:
            return self.source_event_id
        return f"{self.source_event_id}:{self.withdrawal_status.value}"

    def normalized_payload(self) -> dict[str, str | None]:
        return {
            "event": self.event_type.value,
            "event_id": self.source_event_id,
            "click_id": self.click_id,
            "trader_id": self.trader_id,
            "amount": str(self.amount) if self.amount is not None else None,
            "occurred_at": self.occurred_at.isoformat(),
            "withdrawal_status": (
                self.withdrawal_status.value
                if self.withdrawal_status is not None
                else None
            ),
            "withdrawal_reference": self.withdrawal_reference,
        }
