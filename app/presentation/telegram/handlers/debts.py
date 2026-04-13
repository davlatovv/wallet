from datetime import date
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery

from app.domain.entities.debt import DebtType, DebtStatus
from app.infrastructure.container import Container
from app.presentation.telegram.keyboards.inline import debt_type_keyboard, confirm_keyboard, action_item_keyboard
from app.presentation.telegram.keyboards.main_menu import main_menu_keyboard
from app.presentation.telegram.states.debt import DebtStates

router = Router(name="debts")


def _format_debt_list(debts) -> str:
    if not debts:
        return "📭 Долгов нет."
    lines = ["💳 <b>Активные долги:</b>\n"]
    for d in debts:
        direction = "Я должен" if d.debt_type == DebtType.I_OWE else "Должны мне"
        due = f" (до {d.due_date})" if d.due_date else ""
        lines.append(f"• {direction} <b>{d.counterparty}</b>: {d.amount:,.2f}{due}")
    return "\n".join(lines)


@router.message(F.text == "💳 Долги")
async def debts_menu(message: Message, container: Container) -> None:
    debts = await container.list_debts.execute(message.from_user.id, status=DebtStatus.ACTIVE)
    await message.answer(
        _format_debt_list(debts),
        parse_mode="HTML",
        reply_markup=debt_type_keyboard(),
    )


@router.callback_query(F.data.startswith("debt_type:"))
async def debt_type_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    debt_type = callback.data.split(":")[1]
    await state.update_data(debt_type=debt_type)
    await state.set_state(DebtStates.waiting_for_counterparty)
    await callback.message.edit_text("Введите имя человека (кредитора/должника):")
    await callback.answer()


@router.message(DebtStates.waiting_for_counterparty)
async def debt_counterparty_entered(message: Message, state: FSMContext) -> None:
    await state.update_data(counterparty=message.text.strip())
    await state.set_state(DebtStates.waiting_for_amount)
    await message.answer("Введите сумму долга:")


@router.message(DebtStates.waiting_for_amount)
async def debt_amount_entered(message: Message, state: FSMContext) -> None:
    try:
        amount = Decimal(message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("Неверная сумма. Введите положительное число.")
        return
    await state.update_data(amount=str(amount))
    await state.set_state(DebtStates.waiting_for_description)
    await message.answer("Добавьте описание (или /skip):")


@router.message(DebtStates.waiting_for_description, F.text == "/skip")
@router.message(DebtStates.waiting_for_description)
async def debt_description_entered(message: Message, state: FSMContext) -> None:
    desc = None if message.text == "/skip" else message.text
    await state.update_data(description=desc)
    await state.set_state(DebtStates.waiting_for_due_date)
    await message.answer("Срок погашения (ГГГГ-ММ-ДД) или /skip:")


@router.message(DebtStates.waiting_for_due_date, F.text == "/skip")
@router.message(DebtStates.waiting_for_due_date)
async def debt_due_date_entered(message: Message, state: FSMContext) -> None:
    due_date_str = None
    if message.text != "/skip":
        try:
            due_date_str = str(date.fromisoformat(message.text.strip()))
        except ValueError:
            await message.answer("Неверный формат. Используйте ГГГГ-ММ-ДД или /skip.")
            return
    await state.update_data(due_date=due_date_str)
    data = await state.get_data()
    debt_type_label = "Я должен" if data["debt_type"] == "i_owe" else "Должны мне"
    await state.set_state(DebtStates.confirming)
    await message.answer(
        f"📋 <b>Подтвердите долг:</b>\n\n"
        f"Тип: {debt_type_label}\n"
        f"Кому/Кто: <b>{data['counterparty']}</b>\n"
        f"Сумма: <b>{Decimal(data['amount']):,.2f}</b>\n"
        f"Срок: {data.get('due_date') or '—'}",
        parse_mode="HTML",
        reply_markup=confirm_keyboard("debt_confirm", "cancel"),
    )


@router.callback_query(DebtStates.confirming, F.data == "debt_confirm")
async def debt_confirmed(callback: CallbackQuery, state: FSMContext, container: Container) -> None:
    data = await state.get_data()
    due = date.fromisoformat(data["due_date"]) if data.get("due_date") else None
    await container.add_debt.execute(
        user_id=callback.from_user.id,
        counterparty=data["counterparty"],
        amount=Decimal(data["amount"]),
        debt_type=DebtType(data["debt_type"]),
        description=data.get("description"),
        due_date=due,
    )
    await state.clear()
    await callback.message.edit_text("✅ Долг записан!")
    await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("debt_settle:"))
async def settle_debt(callback: CallbackQuery, container: Container) -> None:
    debt_id = int(callback.data.split(":")[1])
    debt = await container.settle_debt.execute(debt_id, callback.from_user.id)
    await callback.answer(f"✅ Долг с {debt.counterparty} закрыт!", show_alert=True)
    await callback.message.delete()
