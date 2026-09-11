import datetime
from dataclasses import dataclass
from decimal import Decimal

from database.models import Product, SignalAsset, User
from database.uow import UnitOfWork
from domain.enums import AuditAction, ProductGrantCondition


class AdminPermissionError(PermissionError):
    pass


class AdminRuleError(ValueError):
    pass


@dataclass(frozen=True, slots=True)
class AdminDashboard:
    date_from: datetime.date
    date_to: datetime.date
    registrations: int
    first_deposits: int
    first_deposit_amount: Decimal
    repeat_deposits: int
    repeat_deposit_amount: Decimal
    signals: int
    diary_entries: int
    active_users: int
    registration_to_first_deposit_rate: Decimal | None
    first_to_repeat_deposit_rate: Decimal | None


class AdminService:
    async def require_admin(self, uow: UnitOfWork, *, telegram_id: int) -> User:
        user = await uow.users.get_by_telegram_id(telegram_id)
        if user is None or not user.is_admin:
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

    async def dashboard(
        self,
        uow: UnitOfWork,
        *,
        date_from: datetime.date,
        date_to: datetime.date,
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
        )
        return AdminDashboard(
            date_from=date_from,
            date_to=date_to,
            registrations=totals.registrations,
            first_deposits=totals.first_deposits,
            first_deposit_amount=totals.first_deposit_amount,
            repeat_deposits=totals.repeat_deposits,
            repeat_deposit_amount=totals.repeat_deposit_amount,
            signals=totals.signals,
            diary_entries=totals.diary_entries,
            active_users=totals.active_users,
            registration_to_first_deposit_rate=_conversion_rate(
                totals.first_deposits,
                totals.registrations,
            ),
            first_to_repeat_deposit_rate=_conversion_rate(
                totals.repeat_deposits,
                totals.first_deposits,
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


def _apply_changes(
    entity: Product | SignalAsset,
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
