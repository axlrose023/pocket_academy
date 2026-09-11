import uuid
from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import Product, UserProductAccess


class ProductDAO:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_published(self, product_id: uuid.UUID) -> Product | None:
        return await self._session.scalar(
            select(Product).where(
                Product.id == product_id, Product.is_published.is_(True)
            )
        )

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
