from aiogram.types import ReplyKeyboardMarkup, KeyboardButton


def main_menu_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [
                KeyboardButton(text="➕ Расход"),
                KeyboardButton(text="➕ Доход"),
            ],
            [
                KeyboardButton(text="📊 Статистика"),
            ],
            [
                KeyboardButton(text="📂 Категории"),
                KeyboardButton(text="🎯 Бюджеты"),
            ],
            [
                KeyboardButton(text="💳 Долги"),
                KeyboardButton(text="🏦 Копилка"),
            ],
            [
                KeyboardButton(text="🔔 Напоминалка"),
            ],
        ],
        resize_keyboard=True,
        persistent=True,
    )
