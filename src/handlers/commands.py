from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message
from dishka import FromDishka
from dishka.integrations.aiogram import inject

from config import Config
from database.uow import UnitOfWork
from domain.clock import Clock
from keyboards import admin_webapp_keyboard, webapp_keyboard
from keyboards.webapp import ASSET_VERSION
from services import UserService
from services.admin import AdminPermissionError, AdminService

commands_router = Router(name="commands_router")


@commands_router.message(CommandStart())
@inject
async def cmd_start(
    message: Message,
    uow: FromDishka[UnitOfWork],
    user_service: FromDishka[UserService],
    clock: FromDishka[Clock],
    config: FromDishka[Config],
) -> None:
    sender = message.from_user
    if sender is None:
        return
    existing_user = await uow.users.get_by_telegram_id(sender.id)
    await user_service.upsert(
        uow,
        telegram_id=sender.id,
        username=sender.username,
        first_name=sender.first_name,
        last_name=sender.last_name,
        language_code=sender.language_code,
        seen_at=clock.now(),
    )
    await uow.commit()
    if config.bot.webapp_url is None:
        await message.answer(
            "Pocket Academy is being configured. Please try again soon."
        )
        return
    greeting = (
        "Welcome to Pocket Academy!"
        if existing_user is None
        else "Welcome back to Pocket Academy!"
    )
    await message.answer(
        greeting,
        reply_markup=webapp_keyboard(config.bot.webapp_url),
    )


@commands_router.message(Command("admin"))
@inject
async def cmd_admin(
    message: Message,
    config: FromDishka[Config],
    uow: FromDishka[UnitOfWork],
    admin_service: FromDishka[AdminService],
) -> None:
    sender = message.from_user
    if sender is None:
        return
    try:
        await admin_service.require_admin(uow, telegram_id=sender.id)
    except AdminPermissionError:
        await message.answer("У тебя нет доступа к админке.")
        return
    if config.api.public_base_url is None:
        await message.answer("Админка ещё настраивается. Попробуй позже.")
        return
    admin_url = f"{config.api.public_base_url.rstrip('/')}/admin/?v={ASSET_VERSION}"
    await message.answer(
        "Открыть админку:",
        reply_markup=admin_webapp_keyboard(admin_url),
    )
