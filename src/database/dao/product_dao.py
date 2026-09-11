import uuid
from decimal import Decimal

from sqlalchemy import and_, exists, or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Product, ProductMaterial, UserProductAccess

FREE_PRODUCT_ACCESS = and_(
    Product.price_pac == 0,
    Product.grant_condition == "none",
)


class ProductDAO:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_published(self, product_id: uuid.UUID) -> Product | None:
        return await self._session.scalar(
            select(Product).where(
                Product.id == product_id, Product.is_published.is_(True)
            )
        )

    async def list_published_with_access(
        self, *, user_id: uuid.UUID
    ) -> list[tuple[Product, bool]]:
        access_exists = exists().where(
            UserProductAccess.user_id == user_id,
            UserProductAccess.product_id == Product.id,
        )
        rows = await self._session.execute(
            select(
                Product,
                or_(access_exists, FREE_PRODUCT_ACCESS).label("has_access"),
            )
            .where(Product.is_published.is_(True))
            .order_by(Product.sort_order, Product.created_at)
        )
        return [(product, bool(has_access)) for product, has_access in rows]

    async def has_access(self, *, user_id: uuid.UUID, product_id: uuid.UUID) -> bool:
        return (
            await self._session.scalar(
                select(UserProductAccess.id).where(
                    UserProductAccess.user_id == user_id,
                    UserProductAccess.product_id == product_id,
                )
            )
            is not None
        )

    async def get_accessible(
        self, *, user_id: uuid.UUID, product_id: uuid.UUID
    ) -> Product | None:
        return await self._session.scalar(
            select(Product)
            .outerjoin(
                UserProductAccess,
                and_(
                    UserProductAccess.product_id == Product.id,
                    UserProductAccess.user_id == user_id,
                ),
            )
            .where(
                Product.id == product_id,
                Product.is_published.is_(True),
                or_(UserProductAccess.id.is_not(None), FREE_PRODUCT_ACCESS),
            )
        )

    async def list_materials(self, product_id: uuid.UUID) -> list[ProductMaterial]:
        return list(
            (
                await self._session.scalars(
                    select(ProductMaterial)
                    .where(ProductMaterial.product_id == product_id)
                    .order_by(ProductMaterial.sort_order, ProductMaterial.created_at)
                )
            ).all()
        )

    async def grant(
        self,
        *,
        user_id: uuid.UUID,
        product_id: uuid.UUID,
        source: str,
        price: Decimal | None = None,
    ) -> UserProductAccess:
        access = UserProductAccess(
            user_id=user_id,
            product_id=product_id,
            source=source,
            purchase_price_pac=price,
        )
        self._session.add(access)
        return access

    async def automatic_products(self, total_deposits: Decimal) -> list[Product]:
        return list(
            (
                await self._session.scalars(
                    select(Product).where(
                        Product.is_published.is_(True),
                        Product.grant_condition == "deposit_threshold",
                        Product.grant_deposit_threshold <= total_deposits,
                    )
                )
            ).all()
        )

    async def registration_products(self) -> list[Product]:
        return list(
            (
                await self._session.scalars(
                    select(Product).where(
                        Product.is_published.is_(True),
                        Product.grant_condition == "registration",
                    )
                )
            ).all()
        )
