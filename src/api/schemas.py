import datetime
import uuid
from decimal import Decimal

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


class UserProfileResponse(BaseModel):
    telegram_id: int
    name: str | None
    username: str | None
    status: str
    total_deposits: Decimal
    pac_balance: Decimal
    is_blocked: bool
    current_status_minimum_deposits: Decimal
    next_status: str | None
    next_status_minimum_deposits: Decimal | None
    remaining_deposits: Decimal


class DiaryEntryRequest(BaseModel):
    profitable_trades: int = Field(ge=0, le=100_000)
    losing_trades: int = Field(ge=0, le=100_000)
    mood: int = Field(ge=1, le=5)
    comment: str | None = Field(default=None, max_length=5_000)


class DiaryEntryResponse(BaseModel):
    entry_day: datetime.date
    profitable_trades: int
    losing_trades: int
    mood: int
    comment: str | None
    reward_granted: bool = False


class NotificationResponse(BaseModel):
    id: uuid.UUID
    notification_type: str
    title: str
    body: str
    created_at: datetime.datetime
    read_at: datetime.datetime | None


class NotificationListResponse(BaseModel):
    notifications: list[NotificationResponse]


class MarkNotificationsReadResponse(BaseModel):
    marked_count: int


class ProductResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    product_type: str
    price_pac: Decimal | None
    grant_condition: str
    grant_deposit_threshold: Decimal | None
    is_available: bool
    external_url: str | None


class ProductListResponse(BaseModel):
    products: list[ProductResponse]


class ProductPurchaseResponse(BaseModel):
    product_id: uuid.UUID
    pac_balance: Decimal


class SignalAssetResponse(BaseModel):
    id: uuid.UUID
    asset_key: str
    label: str
    category: str
    is_otc: bool
    is_popular: bool


class SignalAssetListResponse(BaseModel):
    assets: list[SignalAssetResponse]


class SignalAvailabilityResponse(BaseModel):
    used: int
    limit: int | None
    next_available_at: datetime.datetime | None


class SignalOverviewResponse(BaseModel):
    is_blocked: bool
    allowed_timeframes: tuple[int, ...]
    standard: SignalAvailabilityResponse
    premium: SignalAvailabilityResponse
    premium_minimum_deposit: Decimal
    is_premium_available: bool


class SignalRequest(BaseModel):
    asset_id: uuid.UUID
    timeframe_seconds: int = Field(gt=0)
    is_premium: bool = False


class SignalResponse(BaseModel):
    id: uuid.UUID
    asset_label: str
    timeframe_seconds: int
    direction: str
    probability: int
    is_premium: bool
    requested_at: datetime.datetime


class SignalListResponse(BaseModel):
    signals: list[SignalResponse]
