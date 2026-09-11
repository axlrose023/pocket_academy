import logging
from dishka import FromDishka
from dishka.integrations.taskiq import inject

from database.uow import UnitOfWork
from .broker import broker

logger = logging.getLogger(__name__)


@broker.task()
@inject
async def example_task(
    user_chat_id: int,
    message: str,
    uow: FromDishka[UnitOfWork],
) -> None:
    logger.info(f"Processing task for user {user_chat_id} with message: {message}")
    
    user = await uow.user_dao.get_by_chat_id(user_chat_id)
    if user:
        logger.info(f"Found user: {user.username}")
    
    await uow.commit()

