import datetime
import hashlib
import json
from dataclasses import dataclass
from typing import Any

from database.models import ExternalEvent
from database.uow import UnitOfWork
from domain.clock import Clock
from domain.enums import ExternalEventType, ExternalProvider
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
    ) -> tuple[ExternalEvent, bool]:
        canonical_payload = json.dumps(
            payload,
            ensure_ascii=False,
            separators=(",", ":"),
            sort_keys=True,
            default=str,
        )
        identity = source_event_id or canonical_payload
        deduplication_key = hashlib.sha256(
            f"{provider.value}:{event_type.value}:{identity}".encode()
        ).hexdigest()
        return await uow.external_events.create_or_get(
            provider=provider.value,
            event_type=event_type.value,
            deduplication_key=deduplication_key,
            source_event_id=source_event_id,
            payload=payload,
            occurred_at=None,
            received_at=self._clock.now(),
        )


@dataclass(frozen=True, slots=True)
class ChatterfyLead:
    telegram_id: int
    click_id: str
    link_chat: str | None
    source_created_at: datetime.datetime | None


class ChatterfyService:
    def __init__(self, event_service: ExternalEventService, clock: Clock) -> None:
        self._event_service = event_service
        self._clock = clock

    async def record_lead(
        self,
        uow: UnitOfWork,
        *,
        lead: ChatterfyLead,
        payload: dict[str, Any],
    ) -> bool:
        await uow.users.ensure_telegram_id(lead.telegram_id)
        _, created = await self._event_service.record(
            uow,
            provider=ExternalProvider.CHATTERFY,
            event_type=ExternalEventType.LEAD,
            payload=payload,
            source_event_id=lead.click_id,
        )
        await uow.attribution.upsert(
            telegram_id=lead.telegram_id,
            click_id=lead.click_id,
            link_chat=lead.link_chat,
            source_created_at=lead.source_created_at,
            recorded_at=self._clock.now(),
        )
        return created


class PocketOptionEventParser:
    _event_types = {
        "registration": ExternalEventType.REGISTRATION,
        "fd": ExternalEventType.FIRST_DEPOSIT,
        "first_deposit": ExternalEventType.FIRST_DEPOSIT,
        "rd": ExternalEventType.REPEAT_DEPOSIT,
        "resale": ExternalEventType.REPEAT_DEPOSIT,
        "repeat_deposit": ExternalEventType.REPEAT_DEPOSIT,
        "withdrawal": ExternalEventType.WITHDRAWAL,
    }
    _event_id_keys = ("event_id", "transaction_id", "tid")

    def parse(self, payload: dict[str, Any]) -> tuple[ExternalEventType, str | None]:
        raw_event_type = str(
            payload.get("event_type") or payload.get("event") or ""
        ).lower()
        event_type = self._event_types.get(raw_event_type)
        if event_type is None:
            raise UnsupportedExternalEventError("Unsupported Pocket Option event type")
        source_event_id = next(
            (
                str(payload[key])
                for key in self._event_id_keys
                if payload.get(key) is not None
            ),
            None,
        )
        return event_type, source_event_id
