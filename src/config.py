import logging
from functools import lru_cache
from pathlib import Path
from typing import final

import pytz
from pydantic import BaseModel, ConfigDict
from pydantic_settings import BaseSettings, SettingsConfigDict
from pytz.tzinfo import DstTzInfo
from yarl import URL

logger = logging.getLogger("CONFIG")
ENV_FILE_NAME = ".env"


class BotConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    token: str
    debug: bool = False
    timezone: DstTzInfo = pytz.timezone("Europe/Kyiv")


class PostgresConfig(BaseModel):
    host: str = "localhost"
    port: int = 5432
    user: str
    password: str
    db: str

    @property
    def dsn(self) -> str:
        return str(
            URL.build(
                scheme="postgresql+asyncpg",
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password,
                path=f"/{self.db}",
            )
        )


class RedisConfig(BaseModel):
    host: str = "localhost"
    port: int = 6379

    @property
    def dsn(self) -> str:
        return str(
            URL.build(
                scheme="redis",
                host=self.host,
                port=self.port,
            )
        )


@final
class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE_NAME,
        env_prefix="BOT_",
        env_nested_delimiter="__",
    )

    ROOT_PATH: Path = Path(__file__).parent.parent.parent

    bot: BotConfig
    postgres: PostgresConfig
    redis: RedisConfig


@lru_cache
def get_config() -> Config:
    config = Config()
    return config
