from functools import lru_cache
from pathlib import Path
from typing import final
from zoneinfo import ZoneInfo

from pydantic import BaseModel, ConfigDict, Field, SecretStr, model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict
from yarl import URL

ENV_FILE_NAME = ".env"


class BotConfig(BaseModel):
    model_config = ConfigDict(arbitrary_types_allowed=True)

    token: SecretStr | None = None
    debug: bool = False
    timezone: str = "UTC"
    webapp_url: str | None = None

    @property
    def tzinfo(self) -> ZoneInfo:
        return ZoneInfo(self.timezone)

    def require_token(self) -> str:
        if self.token is None or not self.token.get_secret_value().strip():
            raise RuntimeError("BOT_BOT__TOKEN is required to run Telegram polling")
        return self.token.get_secret_value()


class PostgresConfig(BaseModel):
    host: str = "localhost"
    port: int = 5432
    user: str = "postgres"
    password: SecretStr = SecretStr("postgres")
    db: str = "pocket_academy"

    @property
    def dsn(self) -> str:
        return str(
            URL.build(
                scheme="postgresql+asyncpg",
                host=self.host,
                port=self.port,
                user=self.user,
                password=self.password.get_secret_value(),
                path=f"/{self.db}",
            )
        )


class RedisConfig(BaseModel):
    host: str = "localhost"
    port: int = 6379
    db: int = 0

    @property
    def dsn(self) -> str:
        return str(
            URL.build(
                scheme="redis",
                host=self.host,
                port=self.port,
                path=f"/{self.db}",
            )
        )


class ApiConfig(BaseModel):
    host: str = "0.0.0.0"
    port: int = 8000
    public_base_url: str | None = None


class RateLimitConfig(BaseModel):
    enabled: bool = True
    window_seconds: int = Field(default=60, gt=0, le=3_600)
    webapp_requests_per_window: int = Field(default=120, gt=0, le=10_000)
    webhook_requests_per_window: int = Field(default=60, gt=0, le=10_000)


class AdminConfig(BaseModel):
    telegram_ids: tuple[int, ...] = ()


class IntegrationConfig(BaseModel):
    pocket_option_registration_url: str | None = None
    pocket_option_registration_url_ru: str | None = None
    pocket_option_click_id_parameter: str = "click_id"
    pocket_option_webhook_secret: SecretStr | None = None
    chatterfly_webhook_secret: SecretStr | None = None
    telegram_init_data_max_age_seconds: int = 86_400


class StorageConfig(BaseModel):
    enabled: bool = False
    endpoint_url: str | None = None
    bucket: str | None = None
    access_key_id: SecretStr | None = None
    secret_access_key: SecretStr | None = None
    region: str = "us-east-1"
    force_path_style: bool = False
    presigned_download_ttl_seconds: int = Field(default=900, ge=60, le=3_600)

    @model_validator(mode="after")
    def validate_enabled_storage(self) -> "StorageConfig":
        if not self.enabled:
            return self
        if self.bucket is None or not self.bucket.strip():
            raise ValueError("BOT_STORAGE__BUCKET is required when storage is enabled")
        if not self.region.strip():
            raise ValueError("BOT_STORAGE__REGION is required when storage is enabled")
        has_access_key = _has_secret_value(self.access_key_id)
        has_secret_key = _has_secret_value(self.secret_access_key)
        if has_access_key != has_secret_key:
            raise ValueError(
                "S3 access key ID and secret access key must be configured together"
            )
        return self


@final
class Config(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=ENV_FILE_NAME,
        env_prefix="BOT_",
        env_nested_delimiter="__",
        extra="ignore",
    )

    root_path: Path = Path(__file__).resolve().parent.parent

    bot: BotConfig = Field(default_factory=BotConfig)
    postgres: PostgresConfig = Field(default_factory=PostgresConfig)
    redis: RedisConfig = Field(default_factory=RedisConfig)
    api: ApiConfig = Field(default_factory=ApiConfig)
    rate_limit: RateLimitConfig = Field(default_factory=RateLimitConfig)
    admin: AdminConfig = Field(default_factory=AdminConfig)
    integrations: IntegrationConfig = Field(default_factory=IntegrationConfig)
    storage: StorageConfig = Field(default_factory=StorageConfig)


@lru_cache
def get_config() -> Config:
    return Config()


def _has_secret_value(value: SecretStr | None) -> bool:
    return value is not None and bool(value.get_secret_value().strip())
