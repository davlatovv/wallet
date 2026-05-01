from datetime import datetime, timezone

from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.domain.entities.category import CategoryEntity
from app.domain.entities.debt import DebtEntity

_MONTHS_RU = ["Янв", "Фев", "Мар", "Апр", "Май", "Июн", "Июл", "Авг", "Сен", "Окт", "Ноя", "Дек"]


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
            ],
            [InlineKeyboardButton(text="📥 Скачать Excel", callback_data="export_xlsx_menu")],
        ]
    )


def report_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📅 Сегодня", callback_data="report:day"),
                InlineKeyboardButton(text="📆 Неделя", callback_data="report:week"),
                InlineKeyboardButton(text="🗓 Месяц", callback_data="report:month"),
            ],
            [InlineKeyboardButton(text="📥 Скачать Excel", callback_data="export_xlsx_menu")],
            [InlineKeyboardButton(text="◀️ К балансу", callback_data="analytics_balance")],
        ]
    )


def export_month_keyboard() -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    now = datetime.now(timezone.utc)
    for i in range(12):
        month = now.month - i
        year = now.year
        if month <= 0:
            month += 12
            year -= 1
        label = f"{_MONTHS_RU[month - 1]} {year}"
        builder.button(text=label, callback_data=f"export_xlsx_month:{year}:{month}")
    builder.adjust(3)
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="analytics_balance"))
    return builder.as_markup()


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


def currency_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="🇺🇸 USD", callback_data="currency:USD"),
                InlineKeyboardButton(text="🇺🇿 UZS", callback_data="currency:UZS"),
                InlineKeyboardButton(text="💵 Наличные", callback_data="currency:CASH"),
            ]
        ]
    )


def debt_picker_keyboard(debts: list[DebtEntity], action_prefix: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for d in debts:
        label = f"{d.counterparty}: {d.amount:,.0f} UZS"
        builder.button(text=label, callback_data=f"{action_prefix}:{d.id}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="✏️ Ввести вручную", callback_data=f"{action_prefix}:manual"))
    builder.row(InlineKeyboardButton(text="◀️ Отмена", callback_data="cancel"))
    return builder.as_markup()


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
