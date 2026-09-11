import uuid
from decimal import Decimal

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    String,
    Text,
)
from sqlalchemy.orm import Mapped, mapped_column

from database.base import Base
from database.fields import uuid_pk


class Product(Base):
    __tablename__ = "products"
    __table_args__ = (
        CheckConstraint(
            "product_type IN ('course', 'module', 'group', 'bot')", name="type_known"
        ),
        CheckConstraint(
            "grant_condition IN ('none', 'registration', 'deposit_threshold')",
            name="grant_condition_known",
        ),
        CheckConstraint(
            "price_pac IS NULL OR price_pac >= 0", name="price_nonnegative"
        ),
        CheckConstraint(
            "grant_condition <> 'deposit_threshold' OR grant_deposit_threshold IS NOT NULL",
            name="threshold_required",
        ),
    )

    id: Mapped[uuid_pk]
    title: Mapped[str] = mapped_column(String(255))
    description: Mapped[str | None] = mapped_column(Text)
    product_type: Mapped[str] = mapped_column(String(16))
    price_pac: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    grant_condition: Mapped[str] = mapped_column(
        String(32), default="none", server_default="none"
    )
    grant_deposit_threshold: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
    external_url: Mapped[str | None] = mapped_column(Text)
    is_published: Mapped[bool] = mapped_column(
        Boolean, default=True, server_default="true"
    )
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class ProductMaterial(Base):
    __tablename__ = "product_materials"
    __table_args__ = (
        Index("product_materials_product_order_idx", "product_id", "sort_order"),
    )

    id: Mapped[uuid_pk]
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    title: Mapped[str] = mapped_column(String(255))
    content_type: Mapped[str] = mapped_column(String(32))
    storage_key: Mapped[str | None] = mapped_column(String(1024))
    external_url: Mapped[str | None] = mapped_column(Text)
    sort_order: Mapped[int] = mapped_column(Integer, default=0, server_default="0")


class UserProductAccess(Base):
    __tablename__ = "user_product_accesses"
    __table_args__ = (
        Index(
            "user_product_accesses_user_product_key",
            "user_id",
            "product_id",
            unique=True,
        ),
        CheckConstraint(
            "source IN ('purchase', 'automatic', 'manual')", name="source_known"
        ),
    )

    id: Mapped[uuid_pk]
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), index=True
    )
    product_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("products.id", ondelete="CASCADE"), index=True
    )
    source: Mapped[str] = mapped_column(String(16))
    purchase_price_pac: Mapped[Decimal | None] = mapped_column(Numeric(14, 2))
