"""Scheduled product operations run by the Taskiq worker."""

from dishka import FromDishka
from dishka.integrations.taskiq import inject

from database.uow import UnitOfWork
from domain.clock import Clock
from services import PocketOptionEventService
from tskiq.broker import broker


@broker.task(schedule=[{"cron": "*/10 * * * *"}])
@inject(patch_module=True)
async def retry_pending_pocket_option_events(
    uow: FromDishka[UnitOfWork],
    pocket_option_event_service: FromDishka[PocketOptionEventService],
) -> int:
    processed_count = await pocket_option_event_service.retry_pending(uow, limit=100)
    await uow.commit()
    return processed_count


@broker.task(schedule=[{"cron": "0 18 * * *"}])
@inject(patch_module=True)
async def create_diary_reminders(
    uow: FromDishka[UnitOfWork],
    clock: FromDishka[Clock],
) -> int:
    created_count = await uow.engagement.add_diary_reminders(
        entry_day=clock.now().date()
    )
    await uow.commit()
    return created_count
