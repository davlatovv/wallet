from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.application.dto.transaction import AddTransactionDTO
from app.infrastructure.container import Container
from app.presentation.telegram.keyboards.inline import categories_keyboard, confirm_keyboard
from app.presentation.telegram.keyboards.main_menu import main_menu_keyboard
from app.presentation.telegram.states.expense import ExpenseStates

router = Router(name="expense")


@router.message(F.text == "➕ Расход")
async def start_expense(message: Message, state: FSMContext, container: Container) -> None:
    categories = await container.list_categories.execute(message.from_user.id, category_type="expense")
    if not categories:
        await message.answer("У вас нет категорий расходов. Сначала создайте категорию в разделе 📂 Категории.")
        return
    await state.set_state(ExpenseStates.waiting_for_category)
    await message.answer(
        "Выберите категорию расхода:",
        reply_markup=categories_keyboard(categories, action="exp_cat", back_callback="cancel"),
    )


@router.callback_query(ExpenseStates.waiting_for_category, F.data.startswith("exp_cat:"))
async def expense_category_selected(callback: CallbackQuery, state: FSMContext) -> None:
    category_id = int(callback.data.split(":")[1])
    await state.update_data(category_id=category_id)
    await state.set_state(ExpenseStates.waiting_for_amount)
    await callback.message.edit_text("Введите сумму расхода:")
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
    await message.answer(
        "Добавьте комментарий (или нажмите /skip чтобы пропустить):"
    )


@router.message(ExpenseStates.waiting_for_note, F.text == "/skip")
@router.message(ExpenseStates.waiting_for_note)
async def expense_note_entered(message: Message, state: FSMContext) -> None:
    note = None if message.text == "/skip" else message.text
    await state.update_data(note=note)

    data = await state.get_data()
    amount = Decimal(data["amount"])
    cat_id = data.get("category_id")

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
