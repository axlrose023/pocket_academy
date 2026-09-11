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

    async def mark_processed(
        self, event: ExternalEvent, *, processed_at: datetime.datetime
    ) -> None:
        event.processing_status = "processed"
        event.processed_at = processed_at
        event.rejection_reason = None

    async def list_received_pocket_option_events(
        self,
        *,
        trader_id: str | None = None,
        click_id: str | None = None,
        limit: int | None = None,
    ) -> list[ExternalEvent]:
        statement = select(ExternalEvent).where(
            ExternalEvent.provider == "pocket_option",
            ExternalEvent.processing_status == "received",
        )
        if trader_id is not None:
            statement = statement.where(
                ExternalEvent.payload["_normalized"]["trader_id"].astext == trader_id
            )
        if click_id is not None:
            statement = statement.where(
                ExternalEvent.payload["_normalized"]["click_id"].astext == click_id
            )
        statement = statement.order_by(
            ExternalEvent.occurred_at,
            ExternalEvent.received_at,
        )
        if limit is not None:
            statement = statement.limit(limit)
        return list((await self._session.scalars(statement)).all())
