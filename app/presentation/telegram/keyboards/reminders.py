from aiogram.types import InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.application.dto.reminder import ReminderDetailDTO
from app.domain.entities.reminder import ReminderType, ReminderStatus

TYPE_LABELS = {
    ReminderType.CREDIT: "💳 Кредит",
    ReminderType.INSTALLMENT: "📆 Рассрочка",
    ReminderType.EDUCATION: "📚 Контракт за учёбу",
    ReminderType.REGULAR: "🔄 Постоянные расходы",
}

TYPE_ICONS = {
    ReminderType.CREDIT: "💳",
    ReminderType.INSTALLMENT: "📆",
    ReminderType.EDUCATION: "📚",
    ReminderType.REGULAR: "🔄",
}


def reminder_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="💳 Кредит", callback_data="rem_type:credit"),
                InlineKeyboardButton(text="📆 Рассрочка", callback_data="rem_type:installment"),
            ],
            [
                InlineKeyboardButton(text="📚 Контракт за учёбу", callback_data="rem_type:education"),
                InlineKeyboardButton(text="🔄 Постоянные расходы", callback_data="rem_type:regular"),
            ],
            [InlineKeyboardButton(text="◀️ Назад", callback_data="rem_back")],
        ]
    )


def credit_payment_type_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="📊 Аннуитетный", callback_data="rem_ptype:annuity"),
                InlineKeyboardButton(text="📉 Дифференциальный", callback_data="rem_ptype:differential"),
            ]
        ]
    )


def reminders_list_keyboard(reminders: list[ReminderDetailDTO]) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for r in reminders:
        icon = TYPE_ICONS.get(r.reminder_type, "🔔")
        date_str = r.next_payment_date.strftime("%d.%m")
        status_mark = " ✅" if r.status == ReminderStatus.COMPLETED else ""
        label = f"{icon} {r.name} ({date_str}){status_mark}"
        builder.button(text=label, callback_data=f"rem_detail:{r.id}")
    builder.adjust(1)
    builder.row(InlineKeyboardButton(text="➕ Добавить", callback_data="rem_new"))
    return builder.as_markup()


def reminder_detail_keyboard(reminder_id: int, is_completed: bool) -> InlineKeyboardMarkup:
    rows = []
    if not is_completed:
        rows.append([
            InlineKeyboardButton(text="✅ Записать платёж", callback_data=f"rem_pay:{reminder_id}"),
        ])
    rows.append([
        InlineKeyboardButton(text="📅 График платежей", callback_data=f"rem_schedule:{reminder_id}"),
        InlineKeyboardButton(text="🗑 Удалить", callback_data=f"rem_delete:{reminder_id}"),
    ])
    rows.append([InlineKeyboardButton(text="◀️ К списку", callback_data="rem_list")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_payment_keyboard(reminder_id: int) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Подтвердить", callback_data=f"rem_pay_confirm:{reminder_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"rem_detail:{reminder_id}"),
            ]
        ]
    )
