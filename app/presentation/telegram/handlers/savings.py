from datetime import date
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.domain.entities.savings import SavingsStatus
from app.infrastructure.container import Container
from app.presentation.telegram.keyboards.inline import confirm_keyboard
from app.presentation.telegram.keyboards.main_menu import main_menu_keyboard
from app.presentation.telegram.states.savings import SavingsStates

router = Router(name="savings")


def savings_list_keyboard(goals) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for g in goals:
        label = f"{g.name} ({g.progress_percent}%)"
        builder.button(text=label, callback_data=f"savings_fund:{g.id}")
    builder.button(text="➕ Новая цель", callback_data="savings_new")
    builder.adjust(1)
    return builder.as_markup()


def _format_goal(g) -> str:
    bar_filled = int(g.progress_percent / 10)
    bar = "█" * bar_filled + "░" * (10 - bar_filled)
    deadline = f"\n📅 Дедлайн: {g.deadline}" if g.deadline else ""
    return (
        f"🏦 <b>{g.name}</b>\n"
        f"[{bar}] {g.progress_percent}%\n"
        f"Накоплено: {g.current_amount:,.2f} / {g.target_amount:,.2f}\n"
        f"Осталось: {g.remaining:,.2f}{deadline}"
    )


@router.message(F.text == "🏦 Копилка")
async def savings_menu(message: Message, container: Container) -> None:
    goals = await container.list_savings.execute(message.from_user.id, active_only=True)
    if not goals:
        await message.answer(
            "🏦 У вас нет активных целей накопления.\n\nСоздайте первую цель:",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="➕ Новая цель", callback_data="savings_new")]]
            ),
        )
        return
    text = "\n\n".join(_format_goal(g) for g in goals)
    await message.answer(text, parse_mode="HTML", reply_markup=savings_list_keyboard(goals))


@router.callback_query(F.data == "savings_new")
async def start_new_goal(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(SavingsStates.waiting_for_name)
    await callback.message.edit_text("Введите название цели накопления:")
    await callback.answer()


@router.message(SavingsStates.waiting_for_name)
async def goal_name_entered(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(SavingsStates.waiting_for_target)
    await message.answer("Введите целевую сумму:")


@router.message(SavingsStates.waiting_for_target)
async def goal_target_entered(message: Message, state: FSMContext) -> None:
    try:
        amount = Decimal(message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("Неверная сумма. Введите положительное число.")
        return
    await state.update_data(target=str(amount))
    await state.set_state(SavingsStates.waiting_for_deadline)
    await message.answer("Установите дедлайн (ГГГГ-ММ-ДД) или /skip:")


@router.message(SavingsStates.waiting_for_deadline, F.text == "/skip")
@router.message(SavingsStates.waiting_for_deadline)
async def goal_deadline_entered(message: Message, state: FSMContext) -> None:
    deadline_str = None
    if message.text != "/skip":
        try:
            deadline_str = str(date.fromisoformat(message.text.strip()))
        except ValueError:
            await message.answer("Неверный формат. Используйте ГГГГ-ММ-ДД или /skip.")
            return
    await state.update_data(deadline=deadline_str)
    data = await state.get_data()
    await state.set_state(SavingsStates.confirming)
    await message.answer(
        f"📋 <b>Новая цель:</b>\n\n"
        f"🎯 Название: <b>{data['name']}</b>\n"
        f"💰 Сумма: <b>{Decimal(data['target']):,.2f}</b>\n"
        f"📅 Дедлайн: {deadline_str or '—'}",
        parse_mode="HTML",
        reply_markup=confirm_keyboard("savings_confirm", "cancel"),
    )


@router.callback_query(SavingsStates.confirming, F.data == "savings_confirm")
async def goal_confirmed(callback: CallbackQuery, state: FSMContext, container: Container) -> None:
    data = await state.get_data()
    deadline = date.fromisoformat(data["deadline"]) if data.get("deadline") else None
    await container.create_savings_goal.execute(
        user_id=callback.from_user.id,
        name=data["name"],
        target_amount=Decimal(data["target"]),
        deadline=deadline,
    )
    await state.clear()
    await callback.message.edit_text(f"✅ Цель <b>{data['name']}</b> создана!", parse_mode="HTML")
    await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("savings_fund:"))
async def start_fund(callback: CallbackQuery, state: FSMContext) -> None:
    goal_id = int(callback.data.split(":")[1])
    await state.update_data(goal_id=goal_id)
    await state.set_state(SavingsStates.waiting_for_fund_amount)
    await callback.message.edit_text("Введите сумму пополнения:")
    await callback.answer()


@router.message(SavingsStates.waiting_for_fund_amount)
async def fund_amount_entered(message: Message, state: FSMContext, container: Container) -> None:
    try:
        amount = Decimal(message.text.strip().replace(",", "."))
        if amount <= 0:
            raise ValueError
    except (InvalidOperation, ValueError):
        await message.answer("Неверная сумма.")
        return
    data = await state.get_data()
    goal = await container.add_to_savings.execute(data["goal_id"], message.from_user.id, amount)
    await state.clear()
    completed_text = "\n\n🎉 <b>Цель достигнута!</b>" if goal.is_completed else ""
    await message.answer(
        f"✅ Пополнено на <b>{amount:,.2f}</b>\n"
        f"Прогресс: {goal.current_amount:,.2f} / {goal.target_amount:,.2f} ({goal.progress_percent}%)"
        f"{completed_text}",
        parse_mode="HTML",
        reply_markup=main_menu_keyboard(),
    )
