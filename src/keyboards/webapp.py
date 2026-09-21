from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

ASSET_VERSION = "20260921-1"


def webapp_keyboard(webapp_url: str | None) -> InlineKeyboardMarkup | None:
    if webapp_url is None:
        return None
    separator = "&" if "?" in webapp_url else "?"
    versioned_url = f"{webapp_url}{separator}v={ASSET_VERSION}"
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Open Pocket Academy",
                    web_app=WebAppInfo(url=versioned_url),
                )
            ]
        ]
    )


def admin_webapp_keyboard(admin_url: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(
                    text="Open Pocket Academy Admin",
                    web_app=WebAppInfo(url=admin_url),
                )
            ]
        ]
    )
