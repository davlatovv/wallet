from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.application.dto.transaction import AddTransactionDTO
from app.domain.entities.reminder import ReminderStatus
from app.infrastructure.container import Container
from app.presentation.telegram.keyboards.inline import categories_keyboard, confirm_keyboard
from app.presentation.telegram.keyboards.main_menu import main_menu_keyboard
from app.presentation.telegram.states.expense import ExpenseStates

router = Router(name="expense")

REMINDER_TYPE_ICONS = {
    "credit": "💳",
    "installment": "📆",
    "education": "📚",
    "regular": "🔄",
}


def _expense_keyboard(categories, active_reminders) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in categories:
        label = f"{cat.icon or ''} {cat.name}".strip()
        builder.button(text=label, callback_data=f"exp_cat:{cat.id}")
    builder.adjust(2)

    if active_reminders:
        builder.row(InlineKeyboardButton(text="── Регулярные платежи ──", callback_data="noop"))
        for r in active_reminders:
            icon = REMINDER_TYPE_ICONS.get(r.reminder_type.value, "🔔")
            label = f"{icon} {r.name} ({r.payment_amount:,.0f})"
            builder.row(InlineKeyboardButton(text=label, callback_data=f"exp_reminder:{r.id}"))

    builder.row(InlineKeyboardButton(text="◀️ Отмена", callback_data="cancel"))
    return builder.as_markup()


@router.message(F.text == "➕ Расход")
async def start_expense(message: Message, state: FSMContext, container: Container) -> None:
    categories = await container.list_categories.execute(message.from_user.id, category_type="expense")
    reminders = await container.list_reminders.execute(message.from_user.id)
    active_reminders = [r for r in reminders if r.status == ReminderStatus.ACTIVE]

    if not categories and not active_reminders:
        await message.answer("У вас нет категорий расходов. Сначала создайте категорию в разделе 📂 Категории.")
        return

    await state.set_state(ExpenseStates.waiting_for_category)
    await message.answer(
        "Выберите категорию расхода:",
        reply_markup=_expense_keyboard(categories, active_reminders),
    )


@router.callback_query(ExpenseStates.waiting_for_category, F.data.startswith("exp_cat:"))
async def expense_category_selected(callback: CallbackQuery, state: FSMContext) -> None:
    category_id = int(callback.data.split(":")[1])
    await state.update_data(category_id=category_id, reminder_id=None)
    await state.set_state(ExpenseStates.waiting_for_amount)
    await callback.message.edit_text("Введите сумму расхода:")
    await callback.answer()


@router.callback_query(ExpenseStates.waiting_for_category, F.data.startswith("exp_reminder:"))
async def expense_reminder_selected(callback: CallbackQuery, state: FSMContext, container: Container) -> None:
    """User selected a reminder item as expense — pre-fill amount and go straight to confirm."""
    reminder_id = int(callback.data.split(":")[1])
    try:
        r = await container.get_reminder_detail.execute(reminder_id, callback.from_user.id)
    except Exception:
        await callback.answer("Напоминание не найдено", show_alert=True)
        return

    await state.update_data(
        category_id=None,
        reminder_id=reminder_id,
        amount=str(r.payment_amount),
        note=r.name,
    )
    await state.set_state(ExpenseStates.confirming)
    await callback.message.edit_text(
        f"📋 <b>Подтвердите расход:</b>\n\n"
        f"💸 Сумма: <b>{r.payment_amount:,.2f}</b>\n"
        f"📝 Платёж: {r.name}",
        parse_mode="HTML",
        reply_markup=confirm_keyboard("exp_confirm", "cancel"),
    )
    await callback.answer()


@router.callback_query(F.data == "noop")
async def noop_callback(callback: CallbackQuery) -> None:
    await callback.answer()


@router.message(ExpenseStates.waiting_for_amount)
async def expense_amount_entered(message: Message, state: FSMContext) -> None:
    try:
        amount = Decimal(message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("Неверная сумма. Введите положительное число, например: 150.50")
        return

    await state.update_data(amount=str(amount))
    await state.set_state(ExpenseStates.waiting_for_note)
    await message.answer("Добавьте комментарий (или нажмите /skip чтобы пропустить):")


@router.message(ExpenseStates.waiting_for_note, F.text == "/skip")
@router.message(ExpenseStates.waiting_for_note)
async def expense_note_entered(message: Message, state: FSMContext) -> None:
    note = None if message.text == "/skip" else message.text
    await state.update_data(note=note)

    data = await state.get_data()
    amount = Decimal(data["amount"])

    await state.set_state(ExpenseStates.confirming)
    text = (
        f"📋 <b>Подтвердите расход:</b>\n\n"
        f"💸 Сумма: <b>{amount:,.2f}</b>\n"
        f"📝 Заметка: {note or '—'}"
    )
    await message.answer(text, parse_mode="HTML", reply_markup=confirm_keyboard("exp_confirm", "cancel"))


@router.callback_query(ExpenseStates.confirming, F.data == "exp_confirm")
async def expense_confirmed(callback: CallbackQuery, state: FSMContext, container: Container) -> None:
    data = await state.get_data()
    dto = AddTransactionDTO(
        user_id=callback.from_user.id,
        amount=Decimal(data["amount"]),
        category_id=data.get("category_id"),
        note=data.get("note"),
    )
    result = await container.add_expense.execute(dto)

    # If this expense came from a reminder — record the payment
    reminder_id = data.get("reminder_id")
    if reminder_id:
        try:
            await container.record_payment.execute(reminder_id, callback.from_user.id)
        except Exception:
            pass  # Don't block the expense if reminder update fails

    await state.clear()

    alert_text = ""
    for alert in result.alerts:
        emoji = "🔴" if alert.is_critical else "🟡"
        pct = int(alert.used_ratio * 100)
        cat = alert.category_name or "Общий"
        alert_text += f"\n{emoji} Бюджет «{cat}»: использовано {pct}% (лимит {alert.limit})"

    await callback.message.edit_text(
        f"✅ Расход <b>{dto.amount:,.2f}</b> добавлен!{alert_text}",
        parse_mode="HTML",
    )
    await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "cancel")
async def cancel_flow(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("❌ Действие отменено.")
    await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()
