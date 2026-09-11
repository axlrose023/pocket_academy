from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo


def webapp_keyboard(webapp_url: str | None) -> InlineKeyboardMarkup | None:
    if webapp_url is None:
        return None
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Open Pocket Academy",
                    web_app=WebAppInfo(url=webapp_url),
                )
            ]
        ]
    )
