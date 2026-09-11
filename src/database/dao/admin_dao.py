import uuid

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from database.models import AuditLog, Product, SignalAsset, User


class AdminDAO:
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def find_user(self, identifier: str) -> User | None:
        if identifier.isdigit():
            return await self._session.scalar(
                select(User).where(User.telegram_id == int(identifier))
            )
        return await self._session.scalar(
            select(User).where(User.username == identifier.lstrip("@"))
        )

    async def set_user_blocked(
        self, user: User, *, blocked: bool, reason: str | None
    ) -> None:
        user.is_manually_blocked = blocked
        user.manual_block_reason = reason if blocked else None

    async def get_product(self, product_id: uuid.UUID) -> Product | None:
        return await self._session.get(Product, product_id)

    async def list_products(self) -> list[Product]:
        return list(
            (
                await self._session.scalars(
                    select(Product).order_by(Product.sort_order)
                )
            ).all()
        )

    async def get_asset(self, asset_id: uuid.UUID) -> SignalAsset | None:
        return await self._session.get(SignalAsset, asset_id)

    async def get_asset_by_key(self, asset_key: str) -> SignalAsset | None:
        return await self._session.scalar(
            select(SignalAsset).where(SignalAsset.asset_key == asset_key)
        )

    async def list_assets(self) -> list[SignalAsset]:
        return list(
            (
                await self._session.scalars(
                    select(SignalAsset).order_by(SignalAsset.sort_order)
                )
            ).all()
        )

    async def add_audit_log(
        self,
        *,
        actor_id: uuid.UUID,
        action: str,
        payload: dict,
        target_user_id: uuid.UUID | None = None,
    ) -> AuditLog:
        audit_log = AuditLog(
            actor_id=actor_id,
            target_user_id=target_user_id,
            action=action,
            payload=payload,
        )
        self._session.add(audit_log)
        return audit_log
