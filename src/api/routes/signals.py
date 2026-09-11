from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, HTTPException, status

from api.schemas import (
    SignalAssetListResponse,
    SignalAssetResponse,
    SignalAvailabilityResponse,
    SignalListResponse,
    SignalOverviewResponse,
    SignalRequest,
    SignalResponse,
)
from api.webapp_auth import WebAppContext, get_webapp_context
from database.models import Signal
from domain.statuses import allowed_timeframes
from services.signals import SignalAvailability, SignalRuleError, SignalService

router = APIRouter(prefix="/signals", tags=["webapp"])


@router.get("/assets", response_model=SignalAssetListResponse)
async def list_signal_assets(
    context: WebAppContext = Depends(get_webapp_context),
) -> SignalAssetListResponse:
    assets = await context.uow.signals.list_active_assets()
    return SignalAssetListResponse(
        assets=[
            SignalAssetResponse(
                id=asset.id,
                asset_key=asset.asset_key,
                label=asset.label,
                category=asset.category,
                is_otc=asset.is_otc,
                is_popular=asset.is_popular,
            )
            for asset in assets
        ]
    )


@router.get("/availability", response_model=SignalOverviewResponse)
@inject
async def get_signal_availability(
    signal_service: FromDishka[SignalService],
    context: WebAppContext = Depends(get_webapp_context),
) -> SignalOverviewResponse:
    overview = await signal_service.overview(context.uow, user=context.user)
    await context.uow.commit()
    return SignalOverviewResponse(
        is_blocked=overview.access.is_blocked,
        allowed_timeframes=allowed_timeframes(overview.access.status_policy),
        standard=_availability_response(overview.standard),
        premium=_availability_response(overview.premium),
        premium_minimum_deposit=overview.premium_minimum_deposit,
        is_premium_available=overview.is_premium_available,
    )


@router.get("", response_model=SignalListResponse)
async def list_recent_signals(
    context: WebAppContext = Depends(get_webapp_context),
) -> SignalListResponse:
    signals = await context.uow.signals.list_recent(user_id=context.user.id, limit=20)
    return SignalListResponse(signals=[_signal_response(signal) for signal in signals])


@router.post("", response_model=SignalResponse)
@inject
async def generate_signal(
    payload: SignalRequest,
    signal_service: FromDishka[SignalService],
    context: WebAppContext = Depends(get_webapp_context),
) -> SignalResponse:
    try:
        signal = await signal_service.generate(
            context.uow,
            user_id=context.user.id,
            asset_id=payload.asset_id,
            timeframe_seconds=payload.timeframe_seconds,
            premium=payload.is_premium,
        )
    except SignalRuleError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    await context.uow.commit()
    return _signal_response(signal)


def _availability_response(
    availability: SignalAvailability,
) -> SignalAvailabilityResponse:
    return SignalAvailabilityResponse(
        used=availability.used,
        limit=availability.limit,
        next_available_at=availability.next_available_at,
    )


def _signal_response(signal: Signal) -> SignalResponse:
    return SignalResponse(
        id=signal.id,
        asset_label=signal.asset_label,
        timeframe_seconds=signal.timeframe_seconds,
        direction=signal.direction,
        probability=signal.probability,
        is_premium=signal.is_premium,
        requested_at=signal.requested_at,
    )
