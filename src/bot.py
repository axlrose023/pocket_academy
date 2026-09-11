from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.base import DefaultKeyBuilder
from aiogram.fsm.storage.redis import RedisStorage

from config import get_config

config = get_config()

bot_default_properties = DefaultBotProperties(parse_mode=ParseMode.HTML)
bot = Bot(token=config.bot.token, default=bot_default_properties)

key_builder = DefaultKeyBuilder(with_destiny=True)
storage = RedisStorage.from_url(config.redis.dsn, key_builder=key_builder)
dp = Dispatcher(storage=storage)
