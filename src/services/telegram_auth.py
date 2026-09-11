import hashlib
import hmac
import json
import time
from dataclasses import dataclass
from urllib.parse import parse_qsl

from config import Config
from services.exceptions import TelegramInitDataError


@dataclass(frozen=True, slots=True)
class TelegramWebAppUser:
    telegram_id: int
    username: str | None
    first_name: str | None
    last_name: str | None
    language_code: str | None


class TelegramWebAppAuthService:
    def __init__(self, config: Config) -> None:
        self._config = config

    def verify(self, init_data: str) -> TelegramWebAppUser:
        token = self._config.bot.require_token()
        values = dict(parse_qsl(init_data, keep_blank_values=True))
        received_hash = values.pop("hash", None)
        if not received_hash:
            raise TelegramInitDataError("Missing Telegram init-data hash")

        auth_date = self._parse_auth_date(values.get("auth_date"))
        now = int(time.time())
        max_age = self._config.integrations.telegram_init_data_max_age_seconds
        if auth_date > now + 60 or now - auth_date > max_age:
            raise TelegramInitDataError("Expired Telegram init data")

        data_check_string = "\n".join(
            f"{key}={value}" for key, value in sorted(values.items())
        )
        secret_key = hmac.new(
            b"WebAppData",
            token.encode(),
            hashlib.sha256,
        ).digest()
        expected_hash = hmac.new(
            secret_key,
            data_check_string.encode(),
            hashlib.sha256,
        ).hexdigest()
        if not hmac.compare_digest(expected_hash, received_hash):
            raise TelegramInitDataError("Invalid Telegram init-data signature")

        try:
            user = json.loads(values["user"])
            return TelegramWebAppUser(
                telegram_id=int(user["id"]),
                username=user.get("username"),
                first_name=user.get("first_name"),
                last_name=user.get("last_name"),
                language_code=user.get("language_code"),
            )
        except (KeyError, TypeError, ValueError, json.JSONDecodeError) as error:
            raise TelegramInitDataError("Invalid Telegram user payload") from error

    @staticmethod
    def _parse_auth_date(raw_auth_date: str | None) -> int:
        try:
            return int(raw_auth_date) if raw_auth_date is not None else -1
        except ValueError as error:
            raise TelegramInitDataError("Invalid Telegram auth date") from error
