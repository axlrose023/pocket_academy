from collections.abc import Mapping
from typing import Any
from urllib.parse import parse_qsl

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, HTTPException, Request, status

from api.schemas import AcceptedEventResponse, ChatterfyLeadRequest
from api.security import require_webhook_secret
from config import Config
from database.uow import UnitOfWork
from domain.enums import ExternalProvider
from services import ChatterfyService, ExternalEventService, PocketOptionEventParser
from services.exceptions import UnsupportedExternalEventError
from services.external_events import ChatterfyLead

router = APIRouter(prefix="/integrations", tags=["integrations"])


@router.api_route(
    "/chatterfy/leads", methods=["GET", "POST"], response_model=AcceptedEventResponse
)
@inject
async def receive_chatterfy_lead(
    request: Request,
    uow: FromDishka[UnitOfWork],
    config: FromDishka[Config],
    chatterfy_service: FromDishka[ChatterfyService],
) -> AcceptedEventResponse:
    require_webhook_secret(request, config.integrations.chatterfy_webhook_secret)
    payload = await _read_payload(request)
    try:
        lead_payload = ChatterfyLeadRequest.model_validate(payload)
    except ValueError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Invalid Chatterfy payload",
        ) from error
    created = await chatterfy_service.record_lead(
        uow,
        lead=ChatterfyLead(
            telegram_id=lead_payload.telegram_id,
            click_id=lead_payload.click_id,
            link_chat=lead_payload.link_chat,
            source_created_at=lead_payload.source_created_at,
        ),
        payload=payload,
    )
    await uow.commit()
    return AcceptedEventResponse(accepted=True, duplicate=not created)


@router.api_route(
    "/pocket-option/events",
    methods=["GET", "POST"],
    response_model=AcceptedEventResponse,
)
@inject
async def receive_pocket_option_event(
    request: Request,
    uow: FromDishka[UnitOfWork],
    config: FromDishka[Config],
    parser: FromDishka[PocketOptionEventParser],
    event_service: FromDishka[ExternalEventService],
) -> AcceptedEventResponse:
    require_webhook_secret(request, config.integrations.pocket_option_webhook_secret)
    payload = await _read_payload(request)
    try:
        event_type, source_event_id = parser.parse(payload)
    except UnsupportedExternalEventError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="Unsupported Pocket Option event",
        ) from error
    _, created = await event_service.record(
        uow,
        provider=ExternalProvider.POCKET_OPTION,
        event_type=event_type,
        payload=payload,
        source_event_id=source_event_id,
    )
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
