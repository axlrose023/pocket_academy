import asyncio
import logging

from dishka import AsyncContainer
from dishka.integrations.aiogram import setup_dishka

from dependencies import get_async_container
from handlers.callback import callbacks_router
from handlers.commands import commands_router
from bot import bot, dp
from utils import setup_logging

setup_logging()
logger = logging.getLogger("MAIN")


def setup() -> AsyncContainer:
    dp.include_router(commands_router)
    dp.include_router(callbacks_router)

    container = get_async_container()
    setup_dishka(container=container, router=dp)
    return container


async def run_polling() -> None:
    container = setup()

    try:
        await bot.delete_webhook()
        logger.info("🚀 Starting bot in polling mode...")
        await dp.start_polling(bot)
    finally:
        await container.close()
        await bot.session.close()


if __name__ == "__main__":
    asyncio.run(run_polling())
