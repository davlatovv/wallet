from aiogram import Router
from aiogram.filters import CommandStart
from aiogram.types import Message

from app.presentation.telegram.keyboards.main_menu import main_menu_keyboard

router = Router(name="start")


@router.message(CommandStart())
async def handle_start(message: Message) -> None:
    name = message.from_user.first_name or "друг"
    await message.answer(
        f"👋 Привет, <b>{name}</b>!\n\n"
        "Я твой финансовый помощник. Помогу отслеживать доходы, расходы и достигать финансовых целей.\n\n"
        "Выбери действие из меню:",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )
