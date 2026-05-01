from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.application.dto.transaction import AddTransactionDTO
from app.domain.entities.debt import DebtType, DebtStatus
from app.infrastructure.container import Container
from app.infrastructure.currency.cbu_client import get_usd_rate
from app.presentation.telegram.keyboards.inline import (
    categories_keyboard, confirm_keyboard, currency_keyboard, debt_picker_keyboard,
)
from app.presentation.telegram.keyboards.main_menu import main_menu_keyboard
from app.presentation.telegram.states.income import IncomeStates

router = Router(name="income")


def _amount_display(data: dict) -> str:
    amount = Decimal(data["amount"])
    currency = data.get("currency", "UZS")
    if currency == "USD":
        original = Decimal(data.get("original_amount", data["amount"]))
        rate = Decimal(data.get("usd_rate", "0"))
        return f"<b>{amount:,.0f} UZS</b> ({original:,.2f} USD × {rate:,.2f})"
    if currency == "CASH":
        return f"<b>{amount:,.2f} UZS</b> (💵 Наличные)"
    return f"<b>{amount:,.2f} UZS</b>"


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
async def income_category_selected(callback: CallbackQuery, state: FSMContext, container: Container) -> None:
    category_id = int(callback.data.split(":")[1])
    await state.update_data(category_id=category_id)

    cat = await container.get_category.execute(category_id, callback.from_user.id)
    if cat and cat.name == "Долги":
        debts = await container.list_debts.execute(callback.from_user.id, status=DebtStatus.ACTIVE)
        owed_to_me = [d for d in debts if d.debt_type == DebtType.OWED_TO_ME]
        if owed_to_me:
            await state.set_state(IncomeStates.waiting_for_debt)
            await callback.message.edit_text(
                "💳 <b>Выберите долг, который вам вернули:</b>",
                parse_mode="HTML",
                reply_markup=debt_picker_keyboard(owed_to_me, "inc_debt"),
            )
            await callback.answer()
            return

    await state.set_state(IncomeStates.waiting_for_amount)
    await callback.message.edit_text("Введите сумму дохода:")
    await callback.answer()


@router.callback_query(IncomeStates.waiting_for_debt, F.data.startswith("inc_debt:"))
async def income_debt_selected(callback: CallbackQuery, state: FSMContext, container: Container) -> None:
    value = callback.data.split(":")[1]
    if value == "manual":
        await state.set_state(IncomeStates.waiting_for_amount)
        await callback.message.edit_text("Введите сумму дохода:")
        await callback.answer()
        return

    debt_id = int(value)
    debts = await container.list_debts.execute(callback.from_user.id, status=DebtStatus.ACTIVE)
    debt = next((d for d in debts if d.id == debt_id), None)
    if not debt:
        await callback.answer("Долг не найден.", show_alert=True)
        return

    await state.update_data(
        debt_id=debt_id,
        amount=str(debt.amount),
        currency="UZS",
        note=f"Возврат долга: {debt.counterparty}",
    )
    await state.set_state(IncomeStates.confirming)
    await callback.message.edit_text(
        f"📋 <b>Подтвердите доход:</b>\n\n"
        f"💰 Сумма: <b>{debt.amount:,.0f} UZS</b>\n"
        f"💳 Долг от <b>{debt.counterparty}</b> будет закрыт",
        parse_mode="HTML",
        reply_markup=confirm_keyboard("inc_confirm", "cancel"),
    )
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
    await state.update_data(original_amount=str(amount))
    await state.set_state(IncomeStates.waiting_for_currency)
    await message.answer(
        f"Сумма: <b>{amount:,.2f}</b>\nВыберите валюту:",
        parse_mode="HTML",
        reply_markup=currency_keyboard(),
    )


@router.callback_query(IncomeStates.waiting_for_currency, F.data.startswith("currency:"))
async def income_currency_selected(callback: CallbackQuery, state: FSMContext) -> None:
    currency = callback.data.split(":")[1]
    data = await state.get_data()
    original_amount = Decimal(data["original_amount"])

    if currency == "USD":
        try:
            rate = await get_usd_rate()
        except Exception:
            await callback.answer("Не удалось получить курс USD. Попробуйте позже.", show_alert=True)
            return
        converted = (original_amount * rate).quantize(Decimal("1"))
        await state.update_data(currency="USD", amount=str(converted), usd_rate=str(rate))
        await callback.message.edit_text(
            f"💱 {original_amount:,.2f} USD × {rate:,.2f} = <b>{converted:,.0f} UZS</b>\n\n"
            "Добавьте комментарий (или /skip):",
            parse_mode="HTML",
        )
    else:
        await state.update_data(currency=currency, amount=data["original_amount"])
        await callback.message.edit_text("Добавьте комментарий (или /skip):")

    await state.set_state(IncomeStates.waiting_for_note)
    await callback.answer()


@router.message(IncomeStates.waiting_for_note, F.text == "/skip")
@router.message(IncomeStates.waiting_for_note)
async def income_note_entered(message: Message, state: FSMContext) -> None:
    note = None if message.text == "/skip" else message.text
    await state.update_data(note=note)
    data = await state.get_data()
    await state.set_state(IncomeStates.confirming)
    await message.answer(
        f"📋 <b>Подтвердите доход:</b>\n\n"
        f"💰 Сумма: {_amount_display(data)}\n"
        f"📝 Заметка: {note or '—'}",
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

    debt_id = data.get("debt_id")
    debt_closed_text = ""
    if debt_id:
        try:
            debt = await container.settle_debt.execute(debt_id, callback.from_user.id)
            debt_closed_text = f"\n💳 Долг от <b>{debt.counterparty}</b> закрыт!"
        except Exception:
            pass

    await state.clear()
    await callback.message.edit_text(
        f"✅ Доход <b>{dto.amount:,.0f} UZS</b> добавлен!{debt_closed_text}",
        parse_mode="HTML",
    )
    await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()
