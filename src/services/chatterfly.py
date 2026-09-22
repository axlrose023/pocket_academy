from database.models import ExternalEvent
from database.uow import UnitOfWork
from domain.clock import Clock
from services.broker_events import PocketOptionEventService
from services.exceptions import AttributionConflictError
from services.external_events import ChatterflyLead


class ChatterflyLeadService:
    def __init__(
        self,
        clock: Clock,
        pocket_option_event_service: PocketOptionEventService,
    ) -> None:
        self._clock = clock
        self._pocket_option_event_service = pocket_option_event_service

    async def process(
        self,
        uow: UnitOfWork,
        *,
        event: ExternalEvent,
        lead: ChatterflyLead,
    ) -> None:
        if event.processing_status == "processed":
            return

        existing_attribution = await uow.attribution.get_by_click_id(lead.click_id)
        if (
            existing_attribution is not None
            and existing_attribution.telegram_id != lead.telegram_id
        ):
            raise AttributionConflictError(
                "click_id is already assigned to another Telegram user"
            )

        await uow.users.upsert_profile(
            telegram_id=lead.telegram_id,
            username=lead.username,
            first_name=lead.first_name,
            last_name=lead.last_name,
            language_code=None,
            last_seen_at=self._clock.now(),
        )
        await uow.attribution.upsert(
            telegram_id=lead.telegram_id,
            click_id=lead.click_id,
            source_created_at=lead.occurred_at,
            recorded_at=self._clock.now(),
        )
        await uow.external_events.mark_processed(
            event,
            processed_at=self._clock.now(),
        )
        await self._pocket_option_event_service.retry_pending_for_click_id(
            uow,
            click_id=lead.click_id,
        )
