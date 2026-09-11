from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends

from api.schemas import (
    DiaryEntryRequest,
    DiaryEntryResponse,
    MarkNotificationsReadResponse,
    NotificationListResponse,
    NotificationResponse,
    UserProfileResponse,
)
from api.webapp_auth import WebAppContext, get_webapp_context
from database.models import DiaryEntry
from domain.statuses import status_progress
from services.access import AccessService
from services.diary import DiaryService

router = APIRouter(prefix="/me", tags=["webapp"])


@router.get("", response_model=UserProfileResponse)
@inject
async def get_profile(
    access_service: FromDishka[AccessService],
    context: WebAppContext = Depends(get_webapp_context),
) -> UserProfileResponse:
    access = await access_service.snapshot(context.uow, user=context.user)
    progress = status_progress(access.total_deposits)
    balance = await context.uow.pac_ledger.balance(context.user.id)
    return UserProfileResponse(
        telegram_id=context.user.telegram_id,
        name=context.user.full_name or context.user.username,
        username=context.user.username,
        status=access.status_policy.status.value,
        total_deposits=access.total_deposits,
        pac_balance=balance,
        is_blocked=access.is_blocked,
        current_status_minimum_deposits=progress.current.minimum_deposits,
        next_status=progress.next.status.value if progress.next is not None else None,
        next_status_minimum_deposits=(
            progress.next.minimum_deposits if progress.next is not None else None
        ),
        remaining_deposits=progress.remaining_deposits,
    )


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


@router.put("/diary", response_model=DiaryEntryResponse)
@inject
async def save_today_diary(
    payload: DiaryEntryRequest,
    diary_service: FromDishka[DiaryService],
    context: WebAppContext = Depends(get_webapp_context),
) -> DiaryEntryResponse:
    result = await diary_service.save_today(
        context.uow,
        user_id=context.user.id,
        today=context.clock.now().date(),
        profitable_trades=payload.profitable_trades,
        losing_trades=payload.losing_trades,
        mood=payload.mood,
        comment=payload.comment,
    )
    await context.uow.commit()
    return _diary_response(result.entry, reward_granted=result.reward_granted)


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
