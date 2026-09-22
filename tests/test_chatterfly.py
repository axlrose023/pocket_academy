import asyncio
import datetime
from types import SimpleNamespace

import pytest

from services.chatterfly import ChatterflyLeadService
from services.exceptions import AttributionConflictError
from services.external_events import ChatterflyLead


class FixedClock:
    def now(self) -> datetime.datetime:
        return datetime.datetime(2026, 9, 22, 12, 0, tzinfo=datetime.UTC)


class FakeAttributionDAO:
    def __init__(self, existing_telegram_id: int | None = None) -> None:
        self.existing_telegram_id = existing_telegram_id
        self.upserted = False

    async def get_by_click_id(self, _: str):
        if self.existing_telegram_id is None:
            return None
        return SimpleNamespace(telegram_id=self.existing_telegram_id)

    async def upsert(self, **_):
        self.upserted = True


class FakeUserDAO:
    def __init__(self) -> None:
        self.upserted = False

    async def upsert_profile(self, **_):
        self.upserted = True


class FakeExternalEventDAO:
    async def mark_processed(self, event, *, processed_at):
        event.processing_status = "processed"
        event.processed_at = processed_at


class FakePocketEventService:
    def __init__(self) -> None:
        self.retried_click_id: str | None = None

    async def retry_pending_for_click_id(self, _, *, click_id: str) -> None:
        self.retried_click_id = click_id


def _lead() -> ChatterflyLead:
    return ChatterflyLead(
        telegram_id=8481190128,
        click_id="click-123",
        chatterfly_id="chat-1",
        username="academy_user",
        first_name="Academy",
        last_name="User",
        occurred_at=FixedClock().now(),
    )


def test_lead_service_persists_user_and_attribution_then_retries_events() -> None:
    attribution = FakeAttributionDAO()
    users = FakeUserDAO()
    pocket_events = FakePocketEventService()
    uow = SimpleNamespace(
        attribution=attribution,
        users=users,
        external_events=FakeExternalEventDAO(),
    )
    event = SimpleNamespace(processing_status="received", processed_at=None)
    service = ChatterflyLeadService(FixedClock(), pocket_events)

    asyncio.run(service.process(uow, event=event, lead=_lead()))

    assert users.upserted
    assert attribution.upserted
    assert event.processing_status == "processed"
    assert pocket_events.retried_click_id == "click-123"


def test_lead_service_rejects_click_assigned_to_another_user() -> None:
    attribution = FakeAttributionDAO(existing_telegram_id=123)
    users = FakeUserDAO()
    uow = SimpleNamespace(
        attribution=attribution,
        users=users,
        external_events=FakeExternalEventDAO(),
    )
    service = ChatterflyLeadService(FixedClock(), FakePocketEventService())

    with pytest.raises(AttributionConflictError):
        asyncio.run(
            service.process(
                uow,
                event=SimpleNamespace(processing_status="received"),
                lead=_lead(),
            )
        )

    assert not users.upserted
    assert not attribution.upserted
