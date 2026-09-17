from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qsl

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException, Request, status

from api.schemas import AcceptedEventResponse
from api.security import require_webhook_secret
from config import Config
from database.uow import UnitOfWork
from domain.enums import ExternalProvider
from services import (
    ExternalEventService,
    PocketOptionEventParser,
    PocketOptionEventService,
)
from services.exceptions import UnsupportedExternalEventError

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.get(
    "/pocket-option/events",
    response_model=AcceptedEventResponse,
    operation_id="receive_pocket_option_event_get",
)
@router.post(
    "/pocket-option/events",
    response_model=AcceptedEventResponse,
    operation_id="receive_pocket_option_event_post",
)
@inject
async def receive_pocket_option_event(
    request: Request,
    uow: FromDishka[UnitOfWork],
    config: FromDishka[Config],
    parser: FromDishka[PocketOptionEventParser],
    event_service: FromDishka[ExternalEventService],
    pocket_option_event_service: FromDishka[PocketOptionEventService],
) -> AcceptedEventResponse:
    require_webhook_secret(request, config.integrations.pocket_option_webhook_secret)
    payload = await _read_payload(request)
    try:
        postback = parser.parse(payload)
    except UnsupportedExternalEventError as error:
        await event_service.record_rejected(
            uow,
            provider=ExternalProvider.POCKET_OPTION,
            payload=payload,
            reason=str(error),
        )
        await uow.commit()
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported Pocket Option event",
        ) from error
    event, created = await event_service.record(
        uow,
        provider=ExternalProvider.POCKET_OPTION,
        event_type=postback.event_type,
        payload=payload,
        source_event_id=postback.source_event_id,
        occurred_at=postback.occurred_at,
        normalized_payload=postback.normalized_payload(),
        deduplication_identity=postback.deduplication_identity,
    )
    await pocket_option_event_service.process(uow, event=event, postback=postback)
    await uow.commit()
    return AcceptedEventResponse(accepted=True, duplicate=not created)


async def _read_payload(request: Request) -> dict[str, Any]:
    payload: dict[str, Any] = dict(request.query_params)
    if request.method == "GET":
        payload.pop("token", None)
        return payload
    try:
        body = await request.json()
    except ValueError:
        body = dict(parse_qsl((await request.body()).decode(), keep_blank_values=True))
    if not isinstance(body, Mapping):
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Webhook payload must be an object",
        )
    payload.update(body)
    payload.pop("token", None)
    return payload
