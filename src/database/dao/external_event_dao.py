import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import ExternalEvent


class ExternalEventDAO:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create_or_get(
        self,
        *,
        provider: str,
        event_type: str,
        deduplication_key: str,
        source_event_id: str | None,
        payload: dict[str, Any],
        occurred_at: datetime.datetime | None,
        received_at: datetime.datetime,
    ) -> tuple[ExternalEvent, bool]:
        statement = insert(ExternalEvent).values(
            provider=provider,
            event_type=event_type,
            deduplication_key=deduplication_key,
            source_event_id=source_event_id,
            processing_status="received",
            payload=payload,
            occurred_at=occurred_at,
            received_at=received_at,
        )
        statement = statement.on_conflict_do_nothing(
            index_elements=[ExternalEvent.deduplication_key],
        ).returning(ExternalEvent)
        event = (await self._session.execute(statement)).scalar_one_or_none()
        if event is not None:
            return event, True

        existing = await self._session.scalar(
            select(ExternalEvent).where(
                ExternalEvent.deduplication_key == deduplication_key,
            )
        )
        if existing is None:
            raise RuntimeError("External event was not persisted")
        return existing, False

    async def mark_processed(self, event: ExternalEvent) -> None:
        event.processing_status = "processed"
