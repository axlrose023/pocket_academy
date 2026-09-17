import secrets
from dataclasses import dataclass

from yarl import URL

from config import Config
from database.models import User
from database.uow import UnitOfWork
from domain.clock import Clock
from services.exceptions import (
    PocketOptionLinkConfigurationError,
    ReregistrationUnavailableError,
)


@dataclass(frozen=True, slots=True)
class PocketOptionRegistrationLink:
    url: str


class PocketOptionLinkService:
    def __init__(self, config: Config, clock: Clock) -> None:
        self._config = config
        self._clock = clock

    async def issue_registration_link(
        self,
        uow: UnitOfWork,
        *,
        user: User,
        force_new: bool,
    ) -> PocketOptionRegistrationLink:
        attribution = None
        if force_new:
            await self._ensure_reregistration_is_available(uow, user=user)
            click_id = self._new_click_id()
        else:
            attribution = await uow.attribution.latest_for_telegram_id(
                user.telegram_id
            )
            click_id = attribution.click_id if attribution is not None else self._new_click_id()

        if force_new or attribution is None:
            now = self._clock.now()
            await uow.attribution.upsert(
                telegram_id=user.telegram_id,
                click_id=click_id,
                link_chat=None,
                source_created_at=now,
                recorded_at=now,
            )
        return PocketOptionRegistrationLink(
            url=self._registration_url(user.language_code, click_id)
        )

    async def _ensure_reregistration_is_available(
        self, uow: UnitOfWork, *, user: User
    ) -> None:
        first_deposit = await uow.finance.first_deposit(user.id)
        settings = await uow.settings.get_or_create()
        if (
            first_deposit is None
            or first_deposit.amount >= settings.minimum_first_deposit
        ):
            raise ReregistrationUnavailableError(
                "Re-registration is available only after a deposit below the activation threshold"
            )

    def _registration_url(self, language_code: str | None, click_id: str) -> str:
        registration_url = self._registration_base_url(language_code)
        try:
            url = URL(registration_url)
        except ValueError as error:
            raise PocketOptionLinkConfigurationError(
                "Pocket Option registration link is configured incorrectly"
            ) from error
        if not url.scheme or not url.host:
            raise PocketOptionLinkConfigurationError(
                "Pocket Option registration link is configured incorrectly"
            )
        parameter = self._config.integrations.pocket_option_click_id_parameter.strip()
        if not parameter:
            raise PocketOptionLinkConfigurationError(
                "Pocket Option click ID parameter is not configured"
            )
        return str(url.update_query({parameter: click_id}))

    def _registration_base_url(self, language_code: str | None) -> str:
        is_russian = (language_code or "").lower().startswith("ru")
        registration_url = (
            self._config.integrations.pocket_option_registration_url_ru
            if is_russian
            else self._config.integrations.pocket_option_registration_url
        )
        registration_url = (
            registration_url or self._config.integrations.pocket_option_registration_url
        )
        if registration_url is None or not registration_url.strip():
            raise PocketOptionLinkConfigurationError(
                "Pocket Option registration link is not configured"
            )
        return registration_url

    @staticmethod
    def _new_click_id() -> str:
        return f"pa_{secrets.token_urlsafe(24)}"
