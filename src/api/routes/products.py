import uuid

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, HTTPException, status

from api.schemas import (
    ProductListResponse,
    ProductPurchaseResponse,
    ProductResponse,
)
from api.webapp_auth import WebAppContext, get_webapp_context
from database.models import Product
from services.products import ProductRuleError, ProductService

router = APIRouter(prefix="/products", tags=["webapp"])


@router.get("", response_model=ProductListResponse)
async def list_products(
    context: WebAppContext = Depends(get_webapp_context),
) -> ProductListResponse:
    products_with_access = await context.uow.products.list_published_with_access(
        user_id=context.user.id
    )
    return ProductListResponse(
        products=[
            _product_response(product, is_available=is_available)
            for product, is_available in products_with_access
        ]
    )


@router.post("/{product_id}/purchase", response_model=ProductPurchaseResponse)
@inject
async def purchase_product(
    product_id: uuid.UUID,
    product_service: FromDishka[ProductService],
    context: WebAppContext = Depends(get_webapp_context),
) -> ProductPurchaseResponse:
    try:
        await product_service.purchase(
            context.uow,
            user_id=context.user.id,
            product_id=product_id,
        )
    except ProductRuleError as error:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail=str(error),
        ) from error
    await context.uow.commit()
    return ProductPurchaseResponse(
        product_id=product_id,
        pac_balance=await context.uow.pac_ledger.balance(context.user.id),
    )


def _product_response(product: Product, *, is_available: bool) -> ProductResponse:
    return ProductResponse(
        id=product.id,
        title=product.title,
        description=product.description,
        product_type=product.product_type,
        price_pac=product.price_pac,
        grant_condition=product.grant_condition,
        grant_deposit_threshold=product.grant_deposit_threshold,
        is_available=is_available,
        external_url=product.external_url if is_available else None,
    )
