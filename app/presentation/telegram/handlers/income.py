from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.application.dto.transaction import AddTransactionDTO
from app.infrastructure.container import Container
from app.presentation.telegram.keyboards.inline import categories_keyboard, confirm_keyboard
from app.presentation.telegram.keyboards.main_menu import main_menu_keyboard
from app.presentation.telegram.states.income import IncomeStates

router = Router(name="income")


@router.message(F.text == "➕ Доход")
async def start_income(message: Message, state: FSMContext, container: Container) -> None:
    categories = await container.list_categories.execute(message.from_user.id, category_type="income")
    if not categories:
        await message.answer("У вас нет категорий доходов.")
        return
    await state.set_state(IncomeStates.waiting_for_category)
    await message.answer(
        "Выберите категорию дохода:",
        reply_markup=categories_keyboard(categories, action="inc_cat", back_callback="cancel"),
    )


@router.callback_query(IncomeStates.waiting_for_category, F.data.startswith("inc_cat:"))
async def income_category_selected(callback: CallbackQuery, state: FSMContext) -> None:
    category_id = int(callback.data.split(":")[1])
    await state.update_data(category_id=category_id)
    await state.set_state(IncomeStates.waiting_for_amount)
    await callback.message.edit_text("Введите сумму дохода:")
    await callback.answer()


@router.message(IncomeStates.waiting_for_amount)
async def income_amount_entered(message: Message, state: FSMContext) -> None:
    try:
        amount = Decimal(message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("Неверная сумма. Введите положительное число.")
        return
    await state.update_data(amount=str(amount))
    await state.set_state(IncomeStates.waiting_for_note)
    await message.answer("Добавьте комментарий (или /skip):")


@router.message(IncomeStates.waiting_for_note, F.text == "/skip")
@router.message(IncomeStates.waiting_for_note)
async def income_note_entered(message: Message, state: FSMContext) -> None:
    note = None if message.text == "/skip" else message.text
    await state.update_data(note=note)
    data = await state.get_data()
    amount = Decimal(data["amount"])
    await state.set_state(IncomeStates.confirming)
    await message.answer(
        f"📋 <b>Подтвердите доход:</b>\n\n💰 Сумма: <b>{amount:,.2f}</b>\n📝 Заметка: {note or '—'}",
        parse_mode="HTML",
        reply_markup=confirm_keyboard("inc_confirm", "cancel"),
    )


@router.callback_query(IncomeStates.confirming, F.data == "inc_confirm")
async def income_confirmed(callback: CallbackQuery, state: FSMContext, container: Container) -> None:
    data = await state.get_data()
    dto = AddTransactionDTO(
        user_id=callback.from_user.id,
        amount=Decimal(data["amount"]),
        category_id=data.get("category_id"),
        note=data.get("note"),
    )
    await container.add_income.execute(dto)
    await state.clear()
    await callback.message.edit_text(
        f"✅ Доход <b>{dto.amount:,.2f}</b> добавлен!",
        parse_mode="HTML",
    )
    await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()
