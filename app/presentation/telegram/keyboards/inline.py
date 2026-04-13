from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.domain.entities.category import CategoryEntity


def categories_keyboard(
    categories: list[CategoryEntity],
    action: str = "select_cat",
    back_callback: str | None = None,
) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in categories:
        label = f"{cat.icon or ''} {cat.name}".strip()
        builder.button(text=label, callback_data=f"{action}:{cat.id}")
    builder.adjust(2)
    if back_callback:
        builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data=back_callback))
    return builder.as_markup()


def confirm_keyboard(confirm_cb: str, cancel_cb: str = "cancel") -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=confirm_cb),
                InlineKeyboardButton(text="❌ Отмена", callback_data=cancel_cb),
            ]
        ]
    )


def period_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Сегодня", callback_data="report:day"),
                InlineKeyboardButton(text="📆 Неделя", callback_data="report:week"),
                InlineKeyboardButton(text="🗓 Месяц", callback_data="report:month"),
            ]
        ]
    )


def debt_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💸 Я должен", callback_data="debt_type:i_owe"),
                InlineKeyboardButton(text="💰 Мне должны", callback_data="debt_type:owed_to_me"),
            ]
        ]
    )


def budget_period_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="День", callback_data="budget_period:daily"),
                InlineKeyboardButton(text="Неделя", callback_data="budget_period:weekly"),
                InlineKeyboardButton(text="Месяц", callback_data="budget_period:monthly"),
            ]
        ]
    )


def action_item_keyboard(item_id: int, entity: str) -> InlineKeyboardMarkup:
    """Generic keyboard for viewing items: delete / close / back."""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Закрыть/оплатить", callback_data=f"{entity}_settle:{item_id}"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"{entity}_delete:{item_id}"),
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data=f"{entity}_list")],
        ]
    )
