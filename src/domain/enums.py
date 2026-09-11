from enum import StrEnum


class ExternalProvider(StrEnum):
    CHATTERFY = "chatterfy"
    POCKET_OPTION = "pocket_option"


class ExternalEventType(StrEnum):
    LEAD = "lead"
    REGISTRATION = "registration"
    FIRST_DEPOSIT = "first_deposit"
    REPEAT_DEPOSIT = "repeat_deposit"
    WITHDRAWAL = "withdrawal"


class ExternalEventStatus(StrEnum):
    RECEIVED = "received"
    PROCESSED = "processed"
    REJECTED = "rejected"


class DepositKind(StrEnum):
    FIRST = "first"
    REPEAT = "repeat"


class WithdrawalStatus(StrEnum):
    NEW = "new"
    CANCELLED = "cancelled"
    SUCCESS = "success"


class PacEntryReason(StrEnum):
    DEPOSIT = "deposit"
    PRODUCT_PURCHASE = "product_purchase"
    DIARY_STREAK_REWARD = "diary_streak_reward"
    MANUAL_ADJUSTMENT = "manual_adjustment"


class ProductType(StrEnum):
    COURSE = "course"
    MODULE = "module"
    GROUP = "group"
    BOT = "bot"


class ProductGrantCondition(StrEnum):
    NONE = "none"
    REGISTRATION = "registration"
    DEPOSIT_THRESHOLD = "deposit_threshold"


class ProductAccessSource(StrEnum):
    PURCHASE = "purchase"
    AUTOMATIC = "automatic"
    MANUAL = "manual"


class MaterialContentType(StrEnum):
    PDF = "pdf"
    VIDEO = "video"
    LINK = "link"


class SignalDirection(StrEnum):
    BUY = "buy"
    SELL = "sell"


class NotificationType(StrEnum):
    REGISTRATION = "registration"
    DEPOSIT = "deposit"
    PRODUCT_ACCESS = "product_access"
    STATUS_CHANGED = "status_changed"
    ACCESS_BLOCKED = "access_blocked"
    ACCESS_RESTORED = "access_restored"
    LOW_FIRST_DEPOSIT = "low_first_deposit"
    DIARY_REMINDER = "diary_reminder"


class ActivityType(StrEnum):
    WEBAPP_OPENED = "webapp_opened"
    SIGNAL_GENERATED = "signal_generated"


class AuditAction(StrEnum):
    BLOCK_USER = "block_user"
    UNBLOCK_USER = "unblock_user"
    CREATE_PRODUCT = "create_product"
    UPDATE_PRODUCT = "update_product"
    DELETE_PRODUCT = "delete_product"
    UPDATE_SIGNAL_SETTINGS = "update_signal_settings"
    UPDATE_SIGNAL_ASSETS = "update_signal_assets"
