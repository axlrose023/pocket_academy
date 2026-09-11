from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage

from config import Config


def create_bot(config: Config) -> Bot:
    return Bot(
        token=config.bot.require_token(),
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )


def create_dispatcher(config: Config) -> Dispatcher:
    storage = RedisStorage.from_url(
        config.redis.dsn,
        key_builder=DefaultKeyBuilder(with_destiny=True),
    )
    return Dispatcher(storage=storage)
