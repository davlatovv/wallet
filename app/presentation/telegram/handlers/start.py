from aiogram import Router
from aiogram.filters import Command, CommandStart
from aiogram.types import Message

from app.presentation.telegram.keyboards.webapp import open_app_keyboard

router = Router(name="start")


@router.message(CommandStart())
@router.message(Command("app"))
async def handle_start(message: Message) -> None:
    """All real functionality lives in the Mini App now (see
    docs/MINIAPP_PLAN.md Phase 5 — the chat-based flows this bot used to
    have were removed once the webapp covered the same ground). This
    handler, and the payment-reminder notifications in
    infrastructure/notifications/scheduler.py, are what's left of the bot."""
    name = message.from_user.first_name or "друг"
    keyboard = open_app_keyboard()
    text = (
        f"👋 Привет, <b>{name}</b>!\n\n"
        "Я твой финансовый помощник. Все операции — доходы, расходы, бюджеты, "
        "долги, копилка и напоминания — теперь в приложении."
    )
    if keyboard is None:
        text += "\n\n⚠️ Приложение временно недоступно: не задан WEBAPP_URL."
    await message.answer(text, parse_mode="HTML", reply_markup=keyboard)
