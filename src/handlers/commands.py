from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message
from dishka import FromDishka
from dishka.integrations.aiogram import inject

from database.uow import UnitOfWork

commands_router = Router(name="commands_router")


@commands_router.message(CommandStart())
@inject
async def cmd_start(
    message: Message,
    uow: FromDishka["UnitOfWork"],
) -> None:
    if message.from_user is None:
        return
    user = await uow.users.get_by_telegram_id(message.from_user.id)

    if not user:
        user = await uow.users.create(
            telegram_id=message.from_user.id,
            first_name=message.from_user.first_name,
            username=message.from_user.username,
            last_name=message.from_user.last_name,
            language_code=message.from_user.language_code,
        )
        await uow.commit()
        await message.answer("👋 Добро пожаловать! Вы успешно зарегистрированы.")
    else:
        await message.answer("👋 С возвращением!")
