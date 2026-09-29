import asyncio
import uuid
from decimal import Decimal
from types import SimpleNamespace

from services.products import ProductService


class FakeUsers:
    async def get_for_update(self, _: uuid.UUID) -> object:
        return object()


class FakeProducts:
    def __init__(self) -> None:
        self.bundle = SimpleNamespace(
            id=uuid.uuid4(),
            title="Full course",
            price_pac=Decimal("339"),
            grant_condition="none",
        )
        self.included = [
            SimpleNamespace(id=uuid.uuid4(), title="Course AI"),
            SimpleNamespace(id=uuid.uuid4(), title="Patterns"),
        ]
        self.grants: list[tuple[uuid.UUID, Decimal | None]] = []

    async def get_published(self, _: uuid.UUID):
        return self.bundle

    async def has_access(self, *, user_id: uuid.UUID, product_id: uuid.UUID) -> bool:
        return False

    async def grant(self, *, user_id, product_id, source, price=None):
        self.grants.append((product_id, price))
        return SimpleNamespace(product_id=product_id)

    async def bundle_products(self, _: uuid.UUID):
        return self.included


class FakeLedger:
    async def balance(self, _: uuid.UUID) -> Decimal:
        return Decimal("400")

    async def add(self, **_: object) -> None:
        return None


class FakeEngagement:
    async def add_notification(self, **_: object) -> None:
        return None


def test_full_course_purchase_grants_all_included_courses() -> None:
    products = FakeProducts()
    uow = SimpleNamespace(
        users=FakeUsers(),
        products=products,
        pac_ledger=FakeLedger(),
        engagement=FakeEngagement(),
    )

    asyncio.run(ProductService().purchase(uow, user_id=uuid.uuid4(), product_id=uuid.uuid4()))

    assert products.grants == [
        (products.bundle.id, Decimal("339")),
        (products.included[0].id, None),
        (products.included[1].id, None),
    ]
