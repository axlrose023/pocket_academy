import datetime
import uuid
from collections.abc import Mapping
from enum import Enum

from dishka import FromDishka
from dishka.integrations.fastapi import inject
from fastapi import APIRouter, Depends, HTTPException, Response, status

from api.admin_auth import AdminContext, get_admin_context
from api.schemas import (
    AdminDashboardResponse,
    AdminProductCreateRequest,
    AdminProductListResponse,
    AdminProductResponse,
    AdminProductUpdateRequest,
    AdminSettingsResponse,
    AdminSettingsUpdateRequest,
    AdminSignalAssetCreateRequest,
    AdminSignalAssetListResponse,
    AdminSignalAssetResponse,
    AdminSignalAssetUpdateRequest,
    AdminUserBlockRequest,
    AdminUserResponse,
)
from database.models import Product, SignalAsset, User
from domain.clock import Clock
from services.access import AccessService
from services.admin import AdminRuleError, AdminService

router = APIRouter(prefix="/admin", tags=["admin"])


@router.get("/dashboard", response_model=AdminDashboardResponse)
@inject
async def get_dashboard(
    admin_service: FromDishka[AdminService],
    clock: FromDishka[Clock],
    date_from: datetime.date | None = None,
    date_to: datetime.date | None = None,
    context: AdminContext = Depends(get_admin_context),
) -> AdminDashboardResponse:
    today = clock.now().date()
    try:
        dashboard = await admin_service.dashboard(
            context.webapp.uow,
            date_from=date_from or today,
            date_to=date_to or today,
        )
    except AdminRuleError as error:
        raise _rule_error(error) from error
    return AdminDashboardResponse(
        date_from=dashboard.date_from,
        date_to=dashboard.date_to,
        registrations=dashboard.registrations,
        first_deposits=dashboard.first_deposits,
        first_deposit_amount=dashboard.first_deposit_amount,
        repeat_deposits=dashboard.repeat_deposits,
        repeat_deposit_amount=dashboard.repeat_deposit_amount,
        signals=dashboard.signals,
        diary_entries=dashboard.diary_entries,
        active_users=dashboard.active_users,
        registration_to_first_deposit_rate=(
            dashboard.registration_to_first_deposit_rate
        ),
        first_to_repeat_deposit_rate=dashboard.first_to_repeat_deposit_rate,
    )


@router.get("/users/{identifier}", response_model=AdminUserResponse)
@inject
async def get_user(
    identifier: str,
    access_service: FromDishka[AccessService],
    context: AdminContext = Depends(get_admin_context),
) -> AdminUserResponse:
    user = await context.webapp.uow.admin.find_user(identifier)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User was not found",
        )
    return await _user_response(context, user, access_service)


@router.patch("/users/{identifier}/block", response_model=AdminUserResponse)
@inject
async def set_user_blocked(
    identifier: str,
    payload: AdminUserBlockRequest,
    admin_service: FromDishka[AdminService],
    access_service: FromDishka[AccessService],
    context: AdminContext = Depends(get_admin_context),
) -> AdminUserResponse:
    user = await context.webapp.uow.admin.find_user(identifier)
    if user is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="User was not found",
        )
    if payload.is_blocked and not payload.reason:
        raise HTTPException(
            status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
            detail="A block reason is required",
        )
    await admin_service.set_user_blocked(
        context.webapp.uow,
        actor=context.user,
        target=user,
        blocked=payload.is_blocked,
        reason=payload.reason,
    )
    await context.webapp.uow.commit()
    return await _user_response(context, user, access_service)


@router.get("/products", response_model=AdminProductListResponse)
async def list_products(
    context: AdminContext = Depends(get_admin_context),
) -> AdminProductListResponse:
    products = await context.webapp.uow.admin.list_products()
    return AdminProductListResponse(
        products=[_product_response(product) for product in products]
    )


@router.post("/products", response_model=AdminProductResponse)
@inject
async def create_product(
    payload: AdminProductCreateRequest,
    admin_service: FromDishka[AdminService],
    context: AdminContext = Depends(get_admin_context),
) -> AdminProductResponse:
    try:
        product = await admin_service.create_product(
            context.webapp.uow,
            actor=context.user,
            title=payload.title,
            description=payload.description,
            product_type=payload.product_type.value,
            price_pac=payload.price_pac,
            grant_condition=payload.grant_condition.value,
            grant_deposit_threshold=payload.grant_deposit_threshold,
            external_url=payload.external_url,
            is_published=payload.is_published,
            sort_order=payload.sort_order,
        )
    except AdminRuleError as error:
        raise _rule_error(error) from error
    await context.webapp.uow.commit()
    return _product_response(product)


@router.patch("/products/{product_id}", response_model=AdminProductResponse)
@inject
async def update_product(
    product_id: uuid.UUID,
    payload: AdminProductUpdateRequest,
    admin_service: FromDishka[AdminService],
    context: AdminContext = Depends(get_admin_context),
) -> AdminProductResponse:
    product = await _require_product(context, product_id)
    changes = _plain_values(payload.model_dump(exclude_unset=True))
    if not changes:
        return _product_response(product)
    try:
        product = await admin_service.update_product(
            context.webapp.uow,
            actor=context.user,
            product=product,
            changes=changes,
        )
    except AdminRuleError as error:
        raise _rule_error(error) from error
    await context.webapp.uow.commit()
    return _product_response(product)


@router.delete("/products/{product_id}", status_code=status.HTTP_204_NO_CONTENT)
@inject
async def archive_product(
    product_id: uuid.UUID,
    admin_service: FromDishka[AdminService],
    context: AdminContext = Depends(get_admin_context),
) -> Response:
    product = await _require_product(context, product_id)
    await admin_service.archive_product(
        context.webapp.uow,
        actor=context.user,
        product=product,
    )
    await context.webapp.uow.commit()
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.get("/signal-assets", response_model=AdminSignalAssetListResponse)
async def list_signal_assets(
    context: AdminContext = Depends(get_admin_context),
) -> AdminSignalAssetListResponse:
    assets = await context.webapp.uow.admin.list_assets()
    return AdminSignalAssetListResponse(
        assets=[_asset_response(asset) for asset in assets]
    )


@router.post("/signal-assets", response_model=AdminSignalAssetResponse)
@inject
async def create_signal_asset(
    payload: AdminSignalAssetCreateRequest,
    admin_service: FromDishka[AdminService],
    context: AdminContext = Depends(get_admin_context),
) -> AdminSignalAssetResponse:
    try:
        asset = await admin_service.create_asset(
            context.webapp.uow,
            actor=context.user,
            asset_key=payload.asset_key,
            label=payload.label,
            category=payload.category,
            is_otc=payload.is_otc,
            is_popular=payload.is_popular,
            sort_order=payload.sort_order,
        )
    except AdminRuleError as error:
        raise _rule_error(error) from error
    await context.webapp.uow.commit()
    return _asset_response(asset)


@router.patch("/signal-assets/{asset_id}", response_model=AdminSignalAssetResponse)
@inject
async def update_signal_asset(
    asset_id: uuid.UUID,
    payload: AdminSignalAssetUpdateRequest,
    admin_service: FromDishka[AdminService],
    context: AdminContext = Depends(get_admin_context),
) -> AdminSignalAssetResponse:
    asset = await _require_asset(context, asset_id)
    changes = _plain_values(payload.model_dump(exclude_unset=True))
    if not changes:
        return _asset_response(asset)
    asset = await admin_service.update_asset(
        context.webapp.uow,
        actor=context.user,
        asset=asset,
        changes=changes,
    )
    await context.webapp.uow.commit()
    return _asset_response(asset)


@router.get("/settings", response_model=AdminSettingsResponse)
async def get_settings(
    context: AdminContext = Depends(get_admin_context),
) -> AdminSettingsResponse:
    settings = await context.webapp.uow.settings.get_or_create()
    await context.webapp.uow.commit()
    return _settings_response(settings)


@router.put("/settings", response_model=AdminSettingsResponse)
@inject
async def update_settings(
    payload: AdminSettingsUpdateRequest,
    admin_service: FromDishka[AdminService],
    context: AdminContext = Depends(get_admin_context),
) -> AdminSettingsResponse:
    await admin_service.update_signal_settings(
        context.webapp.uow,
        actor=context.user,
        minimum_first_deposit=payload.minimum_first_deposit,
        premium_minimum_deposit=payload.premium_minimum_deposit,
        premium_daily_limit=payload.premium_daily_limit,
        manager_telegram_url=payload.manager_telegram_url,
    )
    await context.webapp.uow.commit()
    settings = await context.webapp.uow.settings.get_or_create()
    return _settings_response(settings)


async def _user_response(
    context: AdminContext,
    user: User,
    access_service: AccessService,
) -> AdminUserResponse:
    access = await access_service.snapshot(context.webapp.uow, user=user)
    return AdminUserResponse(
        telegram_id=user.telegram_id,
        name=user.full_name or user.username,
        username=user.username,
        total_deposits=access.total_deposits,
        pac_balance=await context.webapp.uow.pac_ledger.balance(user.id),
        status=access.status_policy.status.value,
        is_blocked=access.is_blocked,
        is_manually_blocked=user.is_manually_blocked,
        manual_block_reason=user.manual_block_reason,
    )


async def _require_product(context: AdminContext, product_id: uuid.UUID) -> Product:
    product = await context.webapp.uow.admin.get_product(product_id)
    if product is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Product was not found",
        )
    return product


async def _require_asset(context: AdminContext, asset_id: uuid.UUID) -> SignalAsset:
    asset = await context.webapp.uow.admin.get_asset(asset_id)
    if asset is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Signal asset was not found",
        )
    return asset


def _product_response(product: Product) -> AdminProductResponse:
    return AdminProductResponse(
        id=product.id,
        title=product.title,
        description=product.description,
        product_type=product.product_type,
        price_pac=product.price_pac,
        grant_condition=product.grant_condition,
        grant_deposit_threshold=product.grant_deposit_threshold,
        external_url=product.external_url,
        is_published=product.is_published,
        sort_order=product.sort_order,
    )


def _asset_response(asset: SignalAsset) -> AdminSignalAssetResponse:
    return AdminSignalAssetResponse(
        id=asset.id,
        asset_key=asset.asset_key,
        label=asset.label,
        category=asset.category,
        is_otc=asset.is_otc,
        is_popular=asset.is_popular,
        is_active=asset.is_active,
        sort_order=asset.sort_order,
    )


def _settings_response(settings) -> AdminSettingsResponse:
    return AdminSettingsResponse(
        minimum_first_deposit=settings.minimum_first_deposit,
        premium_minimum_deposit=settings.premium_minimum_deposit,
        premium_daily_limit=settings.premium_daily_limit,
        manager_telegram_url=settings.manager_telegram_url,
    )


def _plain_values(values: Mapping[str, object]) -> dict[str, object]:
    return {
        field_name: value.value if isinstance(value, Enum) else value
        for field_name, value in values.items()
    }


def _rule_error(error: AdminRuleError) -> HTTPException:
    return HTTPException(
        status_code=status.HTTP_422_UNPROCESSABLE_ENTITY,
        detail=str(error),
    )
