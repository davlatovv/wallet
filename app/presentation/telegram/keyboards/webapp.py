from aiogram.types import InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo

from app.config.settings import settings


def open_app_keyboard(path: str = "", text: str = "🚀 Открыть приложение") -> InlineKeyboardMarkup | None:
    """A single button that opens the Mini App. Returns None when WEBAPP_URL
    isn't configured (dev without a tunnel yet — see docs/MINIAPP_PLAN.md
    task 0.4), so callers can fall back to a plain-text message instead of
    sending a button Telegram would reject (web_app buttons require an
    https URL)."""
    if not settings.webapp_url:
        return None
    url = settings.webapp_url.rstrip("/") + path
    return InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text=text, web_app=WebAppInfo(url=url))]]
    )
