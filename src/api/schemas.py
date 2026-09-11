import datetime

from pydantic import AliasChoices, BaseModel, ConfigDict, Field


class TelegramSessionRequest(BaseModel):
    init_data: str = Field(min_length=1)


class TelegramSessionResponse(BaseModel):
    telegram_id: int
    first_name: str | None


class ChatterfyLeadRequest(BaseModel):
    model_config = ConfigDict(populate_by_name=True)

    telegram_id: int = Field(validation_alias=AliasChoices("tg_id", "chat_id"))
    click_id: str = Field(
        min_length=1, validation_alias=AliasChoices("click_id", "clickid")
    )
    link_chat: str | None = None
    source_created_at: datetime.datetime | None = Field(
        default=None,
        validation_alias=AliasChoices("source_created_at", "created_at", "started_at"),
    )


class AcceptedEventResponse(BaseModel):
    accepted: bool
    duplicate: bool
