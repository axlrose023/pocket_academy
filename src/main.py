import asyncio
import logging

from aiogram import Bot, Dispatcher
from dishka import AsyncContainer
from dishka.integrations.aiogram import setup_dishka

from bot import create_bot, create_dispatcher
from config import Config, get_config
from database.engine import engine
from dependencies import get_async_container
from handlers.callback import callbacks_router
from handlers.commands import commands_router
from utils import setup_logging

setup_logging()
logger = logging.getLogger("MAIN")


def setup(
    config: Config,
    telegram_bot: Bot,
    dispatcher: Dispatcher,
) -> AsyncContainer:
    dispatcher.include_router(commands_router)
    dispatcher.include_router(callbacks_router)

    container = get_async_container(config=config, telegram_bot=telegram_bot)
    setup_dishka(container=container, router=dispatcher)
    return container


async def run_polling() -> None:
    config = get_config()
    telegram_bot = create_bot(config)
    dispatcher = create_dispatcher(config)
    container = setup(config, telegram_bot, dispatcher)

    try:
        await telegram_bot.delete_webhook()
        logger.info("Starting bot in polling mode")
        await dispatcher.start_polling(telegram_bot)
    finally:
        await container.close()
        await dispatcher.storage.close()
        await telegram_bot.session.close()
        await engine.dispose()


if __name__ == "__main__":
    asyncio.run(run_polling())
