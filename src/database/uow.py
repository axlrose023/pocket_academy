from typing import Self, Any

from sqlalchemy.ext.asyncio import AsyncSession

from database.dao.attribution_dao import AttributionDAO
from database.dao.admin_dao import AdminDAO
from database.dao.external_event_dao import ExternalEventDAO
from database.dao.engagement_dao import EngagementDAO
from database.dao.finance_dao import FinanceDAO
from database.dao.ledger_dao import PacLedgerDAO
from database.dao.product_dao import ProductDAO
from database.dao.signal_dao import SignalDAO
from database.dao.settings_dao import SettingsDAO
from database.dao.user_dao import UserDAO


class UnitOfWork:
    session: AsyncSession
    users: UserDAO
    attribution: AttributionDAO
    external_events: ExternalEventDAO
    finance: FinanceDAO
    pac_ledger: PacLedgerDAO
    signals: SignalDAO
    settings: SettingsDAO
    products: ProductDAO
    engagement: EngagementDAO
    admin: AdminDAO

    def __init__(self: Self, session: AsyncSession):
        self.session = session
        self.users = UserDAO(session)
        self.attribution = AttributionDAO(session)
        self.external_events = ExternalEventDAO(session)
        self.finance = FinanceDAO(session)
        self.pac_ledger = PacLedgerDAO(session)
        self.signals = SignalDAO(session)
        self.settings = SettingsDAO(session)
        self.products = ProductDAO(session)
        self.engagement = EngagementDAO(session)
        self.admin = AdminDAO(session)

    async def commit(self: Self):
        await self.session.commit()

    async def flush(self: Self):
        await self.session.flush()

    async def refresh(self: Self, instance: Any):
        await self.session.refresh(instance)

    async def rollback(self: Self):
        await self.session.rollback()

    async def close(self: Self):
        await self.session.close()

    async def __aenter__(self: Self) -> Self:
        return self

    async def __aexit__(self: Self, exc_type, exc_val, exc_tb):
        if exc_type:
            await self.rollback()
        await self.close()
