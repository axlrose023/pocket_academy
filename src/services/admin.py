from decimal import Decimal

from database.models import Product, SignalAsset, User
from database.uow import UnitOfWork


class AdminPermissionError(PermissionError):
    pass


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
        target: User,
        blocked: bool,
        reason: str | None,
    ) -> None:
        await uow.admin.set_user_blocked(target, blocked=blocked, reason=reason)

    async def create_product(
        self,
        uow: UnitOfWork,
        *,
        title: str,
        product_type: str,
        price_pac: Decimal | None,
    ) -> Product:
        product = Product(title=title, product_type=product_type, price_pac=price_pac)
        uow.session.add(product)
        return product

    async def update_signal_settings(
        self,
        uow: UnitOfWork,
        *,
        premium_minimum_deposit: Decimal,
        premium_daily_limit: int,
        manager_telegram_url: str | None,
    ) -> None:
        settings = await uow.settings.get_or_create()
        settings.premium_minimum_deposit = premium_minimum_deposit
        settings.premium_daily_limit = premium_daily_limit
        settings.manager_telegram_url = manager_telegram_url

    async def create_asset(
        self,
        uow: UnitOfWork,
        *,
        asset_key: str,
        label: str,
        category: str,
        is_otc: bool,
        is_popular: bool,
    ) -> SignalAsset:
        asset = SignalAsset(
            asset_key=asset_key,
            label=label,
            category=category,
            is_otc=is_otc,
            is_popular=is_popular,
        )
        uow.session.add(asset)
        return asset
