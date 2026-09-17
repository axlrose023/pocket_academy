import datetime
import uuid
from decimal import Decimal

from pydantic import BaseModel, Field

from domain.enums import MaterialContentType, ProductGrantCondition, ProductType


class TelegramSessionRequest(BaseModel):
    init_data: str = Field(min_length=1)


class TelegramSessionResponse(BaseModel):
    telegram_id: int
    first_name: str | None


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
    is_registered: bool
    has_deposit: bool
    first_deposit_amount: Decimal | None
    minimum_first_deposit: Decimal
    is_low_first_deposit: bool
    manager_telegram_url: str | None
    current_status_minimum_deposits: Decimal
    next_status: str | None
    next_status_minimum_deposits: Decimal | None
    remaining_deposits: Decimal


class PocketOptionRegistrationLinkRequest(BaseModel):
    force_new: bool = False


class PocketOptionRegistrationLinkResponse(BaseModel):
    url: str


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


class DiaryEntryListResponse(BaseModel):
    entries: list[DiaryEntryResponse]


class DepositResponse(BaseModel):
    amount: Decimal
    kind: str
    occurred_at: datetime.datetime


class DepositListResponse(BaseModel):
    deposits: list[DepositResponse]


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


class ProductMaterialResponse(BaseModel):
    id: uuid.UUID
    title: str
    content_type: MaterialContentType
    external_url: str | None
    sort_order: int


class ProductMaterialListResponse(BaseModel):
    materials: list[ProductMaterialResponse]


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
    is_registered: bool
    has_deposit: bool
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


class AdminUserResponse(BaseModel):
    telegram_id: int
    name: str | None
    username: str | None
    trader_ids: list[str]
    click_id: str | None
    total_deposits: Decimal
    pac_balance: Decimal
    status: str
    is_blocked: bool
    is_manually_blocked: bool
    is_manually_unblocked: bool
    manual_block_reason: str | None


class AdminUserBlockRequest(BaseModel):
    is_blocked: bool
    reason: str | None = Field(default=None, max_length=500)


class AdminUserSummaryResponse(BaseModel):
    telegram_id: int
    name: str | None
    username: str | None
    status: str
    total_deposits: Decimal
    registered_at: datetime.datetime | None


class AdminUserListResponse(BaseModel):
    users: list[AdminUserSummaryResponse]


class AdminUserDiaryEntryResponse(BaseModel):
    entry_day: datetime.date
    profitable_trades: int
    losing_trades: int
    mood: int
    comment: str | None


class AdminUserDiarySeriesPointResponse(BaseModel):
    period_start: datetime.date
    entry_count: int
    average_profitable_trades: Decimal | None
    average_losing_trades: Decimal | None
    average_mood: Decimal | None


class AdminUserDiaryReportResponse(BaseModel):
    entry_count: int
    average_profitable_trades: Decimal | None
    average_losing_trades: Decimal | None
    average_mood: Decimal | None
    mood_distribution: tuple[int, int, int, int, int]
    entries: list[AdminUserDiaryEntryResponse]
    series: list[AdminUserDiarySeriesPointResponse]


class AdminProductResponse(BaseModel):
    id: uuid.UUID
    title: str
    description: str | None
    product_type: ProductType
    price_pac: Decimal | None
    grant_condition: ProductGrantCondition
    grant_deposit_threshold: Decimal | None
    external_url: str | None
    is_published: bool
    sort_order: int


class AdminProductListResponse(BaseModel):
    products: list[AdminProductResponse]


class AdminProductMaterialResponse(BaseModel):
    id: uuid.UUID
    product_id: uuid.UUID
    title: str
    content_type: MaterialContentType
    storage_key: str | None
    external_url: str | None
    sort_order: int


class AdminProductMaterialListResponse(BaseModel):
    materials: list[AdminProductMaterialResponse]


class AdminProductMaterialCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    content_type: MaterialContentType
    storage_key: str | None = Field(default=None, max_length=1_024)
    external_url: str | None = Field(default=None, max_length=2_000)
    sort_order: int = Field(default=0, ge=0)


class AdminProductMaterialUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    content_type: MaterialContentType | None = None
    storage_key: str | None = Field(default=None, max_length=1_024)
    external_url: str | None = Field(default=None, max_length=2_000)
    sort_order: int | None = Field(default=None, ge=0)


class AdminProductCreateRequest(BaseModel):
    title: str = Field(min_length=1, max_length=255)
    description: str | None = None
    product_type: ProductType
    price_pac: Decimal | None = Field(default=None, ge=0)
    grant_condition: ProductGrantCondition = ProductGrantCondition.NONE
    grant_deposit_threshold: Decimal | None = Field(default=None, ge=0)
    external_url: str | None = Field(default=None, max_length=2_000)
    is_published: bool = True
    sort_order: int = Field(default=0, ge=0)


class AdminProductUpdateRequest(BaseModel):
    title: str | None = Field(default=None, min_length=1, max_length=255)
    description: str | None = None
    product_type: ProductType | None = None
    price_pac: Decimal | None = Field(default=None, ge=0)
    grant_condition: ProductGrantCondition | None = None
    grant_deposit_threshold: Decimal | None = Field(default=None, ge=0)
    external_url: str | None = Field(default=None, max_length=2_000)
    is_published: bool | None = None
    sort_order: int | None = Field(default=None, ge=0)


class AdminSignalAssetResponse(BaseModel):
    id: uuid.UUID
    asset_key: str
    label: str
    category: str
    is_otc: bool
    is_popular: bool
    is_active: bool
    sort_order: int


class AdminSignalAssetListResponse(BaseModel):
    assets: list[AdminSignalAssetResponse]


class AdminSignalAssetCreateRequest(BaseModel):
    asset_key: str = Field(min_length=1, max_length=64, pattern=r"^[A-Z0-9_./-]+$")
    label: str = Field(min_length=1, max_length=128)
    category: str = Field(min_length=1, max_length=64)
    is_otc: bool = False
    is_popular: bool = False
    sort_order: int = Field(default=0, ge=0)


class AdminSignalAssetUpdateRequest(BaseModel):
    label: str | None = Field(default=None, min_length=1, max_length=128)
    category: str | None = Field(default=None, min_length=1, max_length=64)
    is_otc: bool | None = None
    is_popular: bool | None = None
    is_active: bool | None = None
    sort_order: int | None = Field(default=None, ge=0)


class AdminSettingsResponse(BaseModel):
    minimum_first_deposit: Decimal
    premium_minimum_deposit: Decimal
    premium_daily_limit: int
    manager_telegram_url: str | None


class AdminSettingsUpdateRequest(BaseModel):
    minimum_first_deposit: Decimal = Field(gt=0)
    premium_minimum_deposit: Decimal = Field(gt=0)
    premium_daily_limit: int = Field(ge=0)
    manager_telegram_url: str | None = Field(default=None, max_length=1_024)


class AdminDashboardResponse(BaseModel):
    date_from: datetime.date
    date_to: datetime.date
    granularity: str
    leads: int
    registrations: int
    deposit_count: int
    deposit_amount: Decimal
    first_deposits: int
    first_deposit_amount: Decimal
    repeat_deposits: int
    repeat_deposit_amount: Decimal
    signals: int
    diary_entries: int
    active_users: int
    webapp_opens: int
    diary_profitable_trades: int
    diary_losing_trades: int
    diary_average_profitable_trades: Decimal | None
    diary_average_losing_trades: Decimal | None
    diary_average_mood: Decimal | None
    diary_mood_distribution: tuple[int, int, int, int, int]
    registration_to_first_deposit_rate: Decimal | None
    first_to_repeat_deposit_rate: Decimal | None
    lead_to_registration_rate: Decimal | None
    lead_to_first_deposit_rate: Decimal | None
    series: list["AdminDashboardSeriesPointResponse"]


class AdminDashboardSeriesPointResponse(BaseModel):
    period_start: datetime.date
    leads: int
    registrations: int
    deposit_count: int
    deposit_amount: Decimal
    first_deposits: int
    first_deposit_amount: Decimal
    repeat_deposits: int
    repeat_deposit_amount: Decimal
    signals: int
    diary_entries: int
    webapp_opens: int
