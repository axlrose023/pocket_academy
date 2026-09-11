import datetime
from dataclasses import dataclass
from decimal import Decimal

from config import Config
from database.models import DiaryEntry, Product, ProductMaterial, SignalAsset, User
from database.uow import UnitOfWork
from domain.enums import AuditAction, NotificationType, ProductGrantCondition
from domain.statuses import UserStatus, deposit_range_for_status, resolve_status


class AdminPermissionError(PermissionError):
    pass


class AdminRuleError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AdminDashboard:
    date_from: datetime.date
    date_to: datetime.date
    granularity: str
    leads: int
    registrations: int
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
    series: tuple["AdminDashboardSeriesPoint", ...]


@dataclass(frozen=True, slots=True)
class AdminDashboardSeriesPoint:
    period_start: datetime.date
    leads: int
    registrations: int
    first_deposits: int
    first_deposit_amount: Decimal
    repeat_deposits: int
    repeat_deposit_amount: Decimal
    signals: int
    diary_entries: int
    webapp_opens: int


@dataclass(frozen=True, slots=True)
class AdminUserSummary:
    telegram_id: int
    name: str | None
    username: str | None
    status: str
    total_deposits: Decimal
    registered_at: datetime.datetime | None


@dataclass(frozen=True, slots=True)
class AdminUserDiaryEntry:
    entry_day: datetime.date
    profitable_trades: int
    losing_trades: int
    mood: int
    comment: str | None


@dataclass(frozen=True, slots=True)
class AdminUserDiarySeriesPoint:
    period_start: datetime.date
    entry_count: int
    average_profitable_trades: Decimal | None
    average_losing_trades: Decimal | None
    average_mood: Decimal | None


@dataclass(frozen=True, slots=True)
class AdminUserDiaryReport:
    entry_count: int
    average_profitable_trades: Decimal | None
    average_losing_trades: Decimal | None
    average_mood: Decimal | None
    mood_distribution: tuple[int, int, int, int, int]
    entries: tuple[AdminUserDiaryEntry, ...]
    series: tuple[AdminUserDiarySeriesPoint, ...]


class AdminService:
    def __init__(self, config: Config) -> None:
        self._bootstrap_admin_ids = frozenset(config.admin.telegram_ids)

    async def require_admin(self, uow: UnitOfWork, *, telegram_id: int) -> User:
        user = await uow.users.get_by_telegram_id(telegram_id)
        if user is None or (
            not user.is_admin and telegram_id not in self._bootstrap_admin_ids
        ):
            raise AdminPermissionError("Administrator access is required")
        return user

    async def set_user_blocked(
        self,
        uow: UnitOfWork,
        *,
        actor: User,
        target: User,
        blocked: bool,
        reason: str | None,
    ) -> None:
        await uow.admin.set_user_blocked(target, blocked=blocked, reason=reason)
        await uow.admin.add_audit_log(
            actor_id=actor.id,
            target_user_id=target.id,
            action=(
                AuditAction.BLOCK_USER if blocked else AuditAction.UNBLOCK_USER
            ).value,
            payload={"reason": reason} if blocked else {},
        )
        await uow.engagement.add_notification(
            user_id=target.id,
            notification_type=(
                NotificationType.ACCESS_BLOCKED
                if blocked
                else NotificationType.ACCESS_RESTORED
            ).value,
            title="Access suspended" if blocked else "Access restored",
            body=(
                reason
                if blocked
                else "Access was restored by a Pocket Academy manager."
            )
            or "Access was suspended by a Pocket Academy manager.",
        )

    async def dashboard(
        self,
        uow: UnitOfWork,
        *,
        date_from: datetime.date,
        date_to: datetime.date,
        granularity: str,
    ) -> AdminDashboard:
        if date_from > date_to:
            raise AdminRuleError("The start date must not be after the end date")
        if date_to - date_from > datetime.timedelta(days=366):
            raise AdminRuleError("The reporting period must not exceed 367 days")
        occurred_from = datetime.datetime.combine(
            date_from,
            datetime.time.min,
            tzinfo=datetime.UTC,
        )
        occurred_until = datetime.datetime.combine(
            date_to + datetime.timedelta(days=1),
            datetime.time.min,
            tzinfo=datetime.UTC,
        )
        totals = await uow.admin.dashboard_totals(
            occurred_from=occurred_from,
            occurred_until=occurred_until,
            day_from=date_from,
            day_until=date_to,
            granularity=granularity,
        )
        return AdminDashboard(
            date_from=date_from,
            date_to=date_to,
            granularity=granularity,
            leads=totals.leads,
            registrations=totals.registrations,
            first_deposits=totals.first_deposits,
            first_deposit_amount=totals.first_deposit_amount,
            repeat_deposits=totals.repeat_deposits,
            repeat_deposit_amount=totals.repeat_deposit_amount,
            signals=totals.signals,
            diary_entries=totals.diary_entries,
            active_users=totals.active_users,
            webapp_opens=totals.webapp_opens,
            diary_profitable_trades=totals.diary_statistics.profitable_trades,
            diary_losing_trades=totals.diary_statistics.losing_trades,
            diary_average_profitable_trades=(
                totals.diary_statistics.average_profitable_trades
            ),
            diary_average_losing_trades=totals.diary_statistics.average_losing_trades,
            diary_average_mood=totals.diary_statistics.average_mood,
            diary_mood_distribution=totals.diary_statistics.mood_distribution,
            registration_to_first_deposit_rate=_conversion_rate(
                totals.first_deposits,
                totals.registrations,
            ),
            first_to_repeat_deposit_rate=_conversion_rate(
                totals.repeat_deposits,
                totals.first_deposits,
            ),
            lead_to_registration_rate=_conversion_rate(
                totals.registrations,
                totals.leads,
            ),
            lead_to_first_deposit_rate=_conversion_rate(
                totals.first_deposits,
                totals.leads,
            ),
            series=tuple(
                AdminDashboardSeriesPoint(
                    period_start=point.period_start,
                    leads=point.leads,
                    registrations=point.registrations,
                    first_deposits=point.first_deposits,
                    first_deposit_amount=point.first_deposit_amount,
                    repeat_deposits=point.repeat_deposits,
                    repeat_deposit_amount=point.repeat_deposit_amount,
                    signals=point.signals,
                    diary_entries=point.diary_entries,
                    webapp_opens=point.webapp_opens,
                )
                for point in totals.series
            ),
        )

    async def list_users(
        self,
        uow: UnitOfWork,
        *,
        status: UserStatus | None,
        registered_from: datetime.date | None,
        registered_to: datetime.date | None,
        minimum_deposits: Decimal | None,
        maximum_deposits: Decimal | None,
        limit: int,
    ) -> list[AdminUserSummary]:
        if registered_from and registered_to and registered_from > registered_to:
            raise AdminRuleError("The start date must not be after the end date")
        if minimum_deposits is not None and maximum_deposits is not None:
            if minimum_deposits > maximum_deposits:
                raise AdminRuleError(
                    "Minimum deposits must not exceed maximum deposits"
                )
        if status is not None:
            minimum_deposits, status_maximum = deposit_range_for_status(status)
            maximum_deposits = status_maximum
        registered_from_at = _day_start(registered_from) if registered_from else None
        registered_until = (
            _day_start(registered_to + datetime.timedelta(days=1))
            if registered_to
            else None
        )
        users = await uow.admin.list_users(
            registered_from=registered_from_at,
            registered_until=registered_until,
            minimum_deposits=minimum_deposits,
            maximum_deposits=maximum_deposits,
            limit=limit,
        )
        return [
            AdminUserSummary(
                telegram_id=summary.user.telegram_id,
                name=summary.user.full_name or summary.user.username,
                username=summary.user.username,
                status=resolve_status(summary.total_deposits).status.value,
                total_deposits=summary.total_deposits,
                registered_at=summary.registered_at,
            )
            for summary in users
        ]

    async def user_diary_report(
        self,
        uow: UnitOfWork,
        *,
        user: User,
        date_from: datetime.date,
        date_to: datetime.date,
        granularity: str,
    ) -> AdminUserDiaryReport:
        if date_from > date_to:
            raise AdminRuleError("The start date must not be after the end date")
        if date_to - date_from > datetime.timedelta(days=366):
            raise AdminRuleError("The reporting period must not exceed 367 days")
        report = await uow.admin.user_diary_report(
            user_id=user.id,
            day_from=date_from,
            day_until=date_to,
            granularity=granularity,
        )
        return AdminUserDiaryReport(
            entry_count=report.statistics.entry_count,
            average_profitable_trades=report.statistics.average_profitable_trades,
            average_losing_trades=report.statistics.average_losing_trades,
            average_mood=report.statistics.average_mood,
            mood_distribution=report.statistics.mood_distribution,
            entries=tuple(_diary_entry(entry) for entry in report.entries),
            series=tuple(
                AdminUserDiarySeriesPoint(
                    period_start=point.period_start,
                    entry_count=point.entry_count,
                    average_profitable_trades=point.average_profitable_trades,
                    average_losing_trades=point.average_losing_trades,
                    average_mood=point.average_mood,
                )
                for point in report.series
            ),
        )

    async def create_product(
        self,
        uow: UnitOfWork,
        *,
        actor: User,
        title: str,
        description: str | None,
        product_type: str,
        price_pac: Decimal | None,
        grant_condition: str,
        grant_deposit_threshold: Decimal | None,
        external_url: str | None,
        is_published: bool,
        sort_order: int,
    ) -> Product:
        product = Product(
            title=title,
            description=description,
            product_type=product_type,
            price_pac=price_pac,
            grant_condition=grant_condition,
            grant_deposit_threshold=grant_deposit_threshold,
            external_url=external_url,
            is_published=is_published,
            sort_order=sort_order,
        )
        self._validate_product(product)
        uow.session.add(product)
        await uow.flush()
        await uow.admin.add_audit_log(
            actor_id=actor.id,
            action=AuditAction.CREATE_PRODUCT.value,
            payload={"product_id": str(product.id)},
        )
        return product

    async def update_product(
        self,
        uow: UnitOfWork,
        *,
        actor: User,
        product: Product,
        changes: dict[str, object],
    ) -> Product:
        _apply_changes(
            product,
            changes,
            allowed_fields={
                "title",
                "description",
                "product_type",
                "price_pac",
                "grant_condition",
                "grant_deposit_threshold",
                "external_url",
                "is_published",
                "sort_order",
            },
        )
        self._validate_product(product)
        await uow.admin.add_audit_log(
            actor_id=actor.id,
            action=AuditAction.UPDATE_PRODUCT.value,
            payload={"product_id": str(product.id), "fields": sorted(changes)},
        )
        return product

    async def archive_product(
        self, uow: UnitOfWork, *, actor: User, product: Product
    ) -> None:
        product.is_published = False
        await uow.admin.add_audit_log(
            actor_id=actor.id,
            action=AuditAction.DELETE_PRODUCT.value,
            payload={"product_id": str(product.id)},
        )

    async def create_product_material(
        self,
        uow: UnitOfWork,
        *,
        actor: User,
        product: Product,
        title: str,
        content_type: str,
        storage_key: str | None,
        external_url: str | None,
        sort_order: int,
    ) -> ProductMaterial:
        material = ProductMaterial(
            product_id=product.id,
            title=title,
            content_type=content_type,
            storage_key=storage_key,
            external_url=external_url,
            sort_order=sort_order,
        )
        self._validate_material(material)
        uow.session.add(material)
        await uow.flush()
        await uow.admin.add_audit_log(
            actor_id=actor.id,
            action=AuditAction.UPDATE_PRODUCT.value,
            payload={"product_id": str(product.id), "material_id": str(material.id)},
        )
        return material

    async def update_product_material(
        self,
        uow: UnitOfWork,
        *,
        actor: User,
        product: Product,
        material: ProductMaterial,
        changes: dict[str, object],
    ) -> ProductMaterial:
        _apply_changes(
            material,
            changes,
            allowed_fields={
                "title",
                "content_type",
                "storage_key",
                "external_url",
                "sort_order",
            },
        )
        self._validate_material(material)
        await uow.admin.add_audit_log(
            actor_id=actor.id,
            action=AuditAction.UPDATE_PRODUCT.value,
            payload={"product_id": str(product.id), "material_id": str(material.id)},
        )
        return material

    async def delete_product_material(
        self,
        uow: UnitOfWork,
        *,
        actor: User,
        product: Product,
        material: ProductMaterial,
    ) -> None:
        await uow.session.delete(material)
        await uow.admin.add_audit_log(
            actor_id=actor.id,
            action=AuditAction.UPDATE_PRODUCT.value,
            payload={
                "product_id": str(product.id),
                "material_id": str(material.id),
                "operation": "delete",
            },
        )

    async def update_signal_settings(
        self,
        uow: UnitOfWork,
        *,
        actor: User,
        minimum_first_deposit: Decimal,
        premium_minimum_deposit: Decimal,
        premium_daily_limit: int,
        manager_telegram_url: str | None,
    ) -> None:
        settings = await uow.settings.get_or_create()
        settings.minimum_first_deposit = minimum_first_deposit
        settings.premium_minimum_deposit = premium_minimum_deposit
        settings.premium_daily_limit = premium_daily_limit
        settings.manager_telegram_url = manager_telegram_url
        await uow.admin.add_audit_log(
            actor_id=actor.id,
            action=AuditAction.UPDATE_SIGNAL_SETTINGS.value,
            payload={
                "minimum_first_deposit": str(minimum_first_deposit),
                "premium_minimum_deposit": str(premium_minimum_deposit),
                "premium_daily_limit": premium_daily_limit,
            },
        )

    async def create_asset(
        self,
        uow: UnitOfWork,
        *,
        actor: User,
        asset_key: str,
        label: str,
        category: str,
        is_otc: bool,
        is_popular: bool,
        sort_order: int,
    ) -> SignalAsset:
        if await uow.admin.get_asset_by_key(asset_key) is not None:
            raise AdminRuleError("Signal asset key is already in use")
        asset = SignalAsset(
            asset_key=asset_key,
            label=label,
            category=category,
            is_otc=is_otc,
            is_popular=is_popular,
            sort_order=sort_order,
        )
        uow.session.add(asset)
        await uow.flush()
        await uow.admin.add_audit_log(
            actor_id=actor.id,
            action=AuditAction.UPDATE_SIGNAL_ASSETS.value,
            payload={"asset_id": str(asset.id), "operation": "create"},
        )
        return asset

    async def update_asset(
        self,
        uow: UnitOfWork,
        *,
        actor: User,
        asset: SignalAsset,
        changes: dict[str, object],
    ) -> SignalAsset:
        _apply_changes(
            asset,
            changes,
            allowed_fields={
                "label",
                "category",
                "is_otc",
                "is_popular",
                "is_active",
                "sort_order",
            },
        )
        await uow.admin.add_audit_log(
            actor_id=actor.id,
            action=AuditAction.UPDATE_SIGNAL_ASSETS.value,
            payload={"asset_id": str(asset.id), "fields": sorted(changes)},
        )
        return asset

    @staticmethod
    def _validate_product(product: Product) -> None:
        has_deposit_condition = (
            product.grant_condition == ProductGrantCondition.DEPOSIT_THRESHOLD.value
        )
        if has_deposit_condition and product.grant_deposit_threshold is None:
            raise AdminRuleError("Deposit threshold is required for this product")
        if not has_deposit_condition:
            product.grant_deposit_threshold = None

    @staticmethod
    def _validate_material(material: ProductMaterial) -> None:
        if material.storage_key is None and material.external_url is None:
            raise AdminRuleError("A storage key or external URL is required")


def _apply_changes(
    entity: Product | ProductMaterial | SignalAsset,
    changes: dict[str, object],
    *,
    allowed_fields: set[str],
) -> None:
    unknown_fields = changes.keys() - allowed_fields
    if unknown_fields:
        raise AdminRuleError("Unexpected mutable fields")
    for field_name, value in changes.items():
        setattr(entity, field_name, value)


def _conversion_rate(numerator: int, denominator: int) -> Decimal | None:
    if denominator == 0:
        return None
    return (Decimal(numerator * 100) / Decimal(denominator)).quantize(Decimal("0.01"))


def _day_start(day: datetime.date) -> datetime.datetime:
    return datetime.datetime.combine(day, datetime.time.min, tzinfo=datetime.UTC)


def _diary_entry(entry: DiaryEntry) -> AdminUserDiaryEntry:
    return AdminUserDiaryEntry(
        entry_day=entry.entry_day,
        profitable_trades=entry.profitable_trades,
        losing_trades=entry.losing_trades,
        mood=entry.mood,
        comment=entry.comment,
    )
