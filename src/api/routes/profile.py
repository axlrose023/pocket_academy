from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, HTTPException, Response, status

from api.schemas import (
    DiaryEntryRequest,
    DiaryEntryResponse,
    DiaryEntryListResponse,
    DiarySaveResponse,
    DepositListResponse,
    DepositResponse,
    MarkNotificationsReadResponse,
    NotificationListResponse,
    NotificationResponse,
    PocketOptionRegistrationLinkRequest,
    PocketOptionRegistrationLinkResponse,
    UserProfileResponse,
)
from api.webapp_auth import WebAppContext, get_webapp_context
from database.models import DiaryEntry
from domain.statuses import status_progress
from domain.enums import ActivityType
from services.access import AccessService
from services.diary import DiaryService
from services.exceptions import (
    PocketOptionLinkConfigurationError,
    PocketOptionLinkError,
)
from services.pocket_option_links import PocketOptionLinkService

router = APIRouter(prefix="/me", tags=["webapp"])


@router.post("/activity/webapp-opened", status_code=status.HTTP_204_NO_CONTENT)
async def record_webapp_open(
    context: WebAppContext = Depends(get_webapp_context),
) -> Response:
    await context.uow.engagement.add_activity(
        user_id=context.user.id,
        activity_type=ActivityType.WEBAPP_OPENED.value,
        occurred_at=context.clock.now(),
    )
    await context.uow.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("", response_model=UserProfileResponse)
@inject
async def get_profile(
    access_service: FromDishka[AccessService],
    context: WebAppContext = Depends(get_webapp_context),
) -> UserProfileResponse:
    access = await access_service.snapshot(context.uow, user=context.user)
    progress = status_progress(access.total_deposits)
    balance = await context.uow.pac_ledger.balance(context.user.id)
    settings = await context.uow.settings.get_or_create()
    first_deposit = await context.uow.finance.first_deposit(context.user.id)
    is_registered = await context.uow.finance.has_account(context.user.id)
    await context.uow.commit()
    return UserProfileResponse(
        telegram_id=context.user.telegram_id,
        name=context.user.full_name or context.user.username,
        username=context.user.username,
        status=access.status_policy.status.value,
        total_deposits=access.total_deposits,
        pac_balance=balance,
        is_blocked=access.is_blocked,
        is_registered=is_registered,
        has_deposit=first_deposit is not None,
        first_deposit_amount=(
            first_deposit.amount if first_deposit is not None else None
        ),
        minimum_first_deposit=settings.minimum_first_deposit,
        is_low_first_deposit=(
            first_deposit is not None
            and first_deposit.amount < settings.minimum_first_deposit
        ),
        manager_telegram_url=settings.manager_telegram_url,
        current_status_minimum_deposits=progress.current.minimum_deposits,
        next_status=progress.next.status.value if progress.next is not None else None,
        next_status_minimum_deposits=(
            progress.next.minimum_deposits if progress.next is not None else None
        ),
        remaining_deposits=progress.remaining_deposits,
    )


@router.post("/pocket-option/link", response_model=PocketOptionRegistrationLinkResponse)
@inject
async def issue_pocket_option_registration_link(
    payload: PocketOptionRegistrationLinkRequest,
    link_service: FromDishka[PocketOptionLinkService],
    context: WebAppContext = Depends(get_webapp_context),
) -> PocketOptionRegistrationLinkResponse:
    try:
        registration_link = await link_service.issue_registration_link(
            context.uow,
            user=context.user,
            force_new=payload.force_new,
        )
    except PocketOptionLinkError as error:
        raise HTTPException(
            status_code=(
                status.HTTP_503_SERVICE_UNAVAILABLE
                if isinstance(error, PocketOptionLinkConfigurationError)
                else status.HTTP_409_CONFLICT
            ),
            detail=str(error),
        ) from error
    await context.uow.commit()
    return PocketOptionRegistrationLinkResponse(url=registration_link.url)


@router.get("/diary", response_model=DiaryEntryResponse | None)
async def get_today_diary(
    context: WebAppContext = Depends(get_webapp_context),
) -> DiaryEntryResponse | None:
    entry = await context.uow.engagement.get_diary_entry(
        user_id=context.user.id,
        entry_day=context.clock.now().date(),
    )
    if entry is None:
        return None
    return _diary_response(entry)


@router.put("/diary", response_model=DiarySaveResponse)
@inject
async def save_today_diary(
    payload: DiaryEntryRequest,
    diary_service: FromDishka[DiaryService],
    context: WebAppContext = Depends(get_webapp_context),
) -> DiarySaveResponse:
    result = await diary_service.save_today(
        context.uow,
        user_id=context.user.id,
        today=context.clock.now().date(),
        profitable_trades=payload.profitable_trades,
        losing_trades=payload.losing_trades,
        mood=payload.mood,
        comment=payload.comment,
    )
    balance = await context.uow.pac_ledger.balance(context.user.id)
    await context.uow.commit()
    return DiarySaveResponse(
        **_diary_response(
            result.entry,
            reward_granted=result.reward_granted,
        ).model_dump(),
        pac_balance=balance,
    )


@router.get("/diary/history", response_model=DiaryEntryListResponse)
async def get_diary_history(
    context: WebAppContext = Depends(get_webapp_context),
) -> DiaryEntryListResponse:
    entries = await context.uow.engagement.list_diary_entries(
        user_id=context.user.id,
        limit=30,
    )
    return DiaryEntryListResponse(entries=[_diary_response(entry) for entry in entries])


@router.get("/deposits", response_model=DepositListResponse)
async def get_recent_deposits(
    context: WebAppContext = Depends(get_webapp_context),
) -> DepositListResponse:
    deposits = await context.uow.finance.list_recent_deposits(
        user_id=context.user.id,
        limit=20,
    )
    return DepositListResponse(
        deposits=[
            DepositResponse(
                amount=deposit.amount,
                kind=deposit.kind,
                occurred_at=deposit.occurred_at,
            )
            for deposit in deposits
        ]
    )


@router.get("/notifications", response_model=NotificationListResponse)
async def get_notifications(
    context: WebAppContext = Depends(get_webapp_context),
) -> NotificationListResponse:
    notifications = await context.uow.engagement.list_notifications(
        user_id=context.user.id,
        limit=50,
    )
    return NotificationListResponse(
        notifications=[
            NotificationResponse(
                id=notification.id,
                notification_type=notification.notification_type,
                title=notification.title,
                body=notification.body,
                created_at=notification.created_at,
                read_at=notification.read_at,
            )
            for notification in notifications
        ]
    )


@router.post("/notifications/read", response_model=MarkNotificationsReadResponse)
async def mark_notifications_read(
    context: WebAppContext = Depends(get_webapp_context),
) -> MarkNotificationsReadResponse:
    marked_count = await context.uow.engagement.mark_notifications_read(
        user_id=context.user.id,
        read_at=context.clock.now(),
    )
    await context.uow.commit()
    return MarkNotificationsReadResponse(marked_count=marked_count)


def _diary_response(
    entry: DiaryEntry,
    *,
    reward_granted: bool = False,
) -> DiaryEntryResponse:
    return DiaryEntryResponse(
        entry_day=entry.entry_day,
        profitable_trades=entry.profitable_trades,
        losing_trades=entry.losing_trades,
        mood=entry.mood,
        comment=entry.comment,
        reward_granted=reward_granted,
    )
