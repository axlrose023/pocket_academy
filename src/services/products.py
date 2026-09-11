import uuid
from decimal import Decimal

from database.models import Product, UserProductAccess
from database.uow import UnitOfWork
from domain.enums import PacEntryReason, ProductAccessSource


class ProductRuleError(ValueError):
    pass


class ProductService:
    async def purchase(
        self, uow: UnitOfWork, *, user_id: uuid.UUID, product_id: uuid.UUID
    ) -> UserProductAccess:
        if await uow.users.get_for_update(user_id) is None:
            raise ProductRuleError("User not found")
        product = await uow.products.get_published(product_id)
        if product is None:
            raise ProductRuleError("Product is unavailable")
        if product.price_pac is None:
            raise ProductRuleError("Product cannot be purchased")
        if product.price_pac == 0 and product.grant_condition == "none":
            raise ProductRuleError("Product is already available")
        if await uow.products.has_access(user_id=user_id, product_id=product_id):
            raise ProductRuleError("Product is already available")
        if (
            product.price_pac > 0
            and await uow.pac_ledger.balance(user_id) < product.price_pac
        ):
            raise ProductRuleError("Insufficient PAC balance")
        access = await uow.products.grant(
            user_id=user_id,
            product_id=product.id,
            source=ProductAccessSource.PURCHASE.value,
            price=product.price_pac,
        )
        if product.price_pac > 0:
            await uow.pac_ledger.add(
                user_id=user_id,
                amount=-product.price_pac,
                reason=PacEntryReason.PRODUCT_PURCHASE.value,
                reference_id=product.id,
                note=product.title,
            )
        await self._notify_access(uow, user_id=user_id, product=product)
        return access

    async def grant_automatic(
        self,
        uow: UnitOfWork,
        *,
        user_id: uuid.UUID,
        registered: bool,
        total_deposits: Decimal,
    ) -> list[UserProductAccess]:
        products = await uow.products.automatic_products(total_deposits)
        if registered:
            products.extend(await uow.products.registration_products())
        accesses: list[UserProductAccess] = []
        for product in products:
            if await uow.products.has_access(user_id=user_id, product_id=product.id):
                continue
            access = await uow.products.grant(
                user_id=user_id,
                product_id=product.id,
                source=ProductAccessSource.AUTOMATIC.value,
            )
            await self._notify_access(uow, user_id=user_id, product=product)
            accesses.append(access)
        return accesses

    @staticmethod
    async def _notify_access(
        uow: UnitOfWork, *, user_id: uuid.UUID, product: Product
    ) -> None:
        await uow.engagement.add_notification(
            user_id=user_id,
            notification_type="product_access",
            title="Product unlocked",
            body=f"{product.title} is now available in Academy.",
        )
