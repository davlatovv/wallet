from datetime import date
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.domain.entities.budget import BudgetPeriod
from app.infrastructure.container import Container
from app.presentation.telegram.keyboards.inline import (
    categories_keyboard,
    budget_period_keyboard,
    confirm_keyboard,
)
from app.presentation.telegram.keyboards.main_menu import main_menu_keyboard
from app.presentation.telegram.states.budget import BudgetStates

router = Router(name="budgets")

PERIOD_LABELS = {
    "daily": "день",
    "weekly": "неделя",
    "monthly": "месяц",
}


def budgets_keyboard(budgets) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for b in budgets:
        cat = b.category_name or "Все расходы"
        label = f"{cat}: {b.limit_amount:,.0f} / {PERIOD_LABELS.get(b.period.value, b.period.value)}"
        builder.button(text=label, callback_data=f"budget_del:{b.id}")
    builder.button(text="➕ Новый бюджет", callback_data="budget_new")
    builder.adjust(1)
    return builder.as_markup()


@router.message(F.text == "🎯 Бюджеты")
async def budgets_menu(message: Message, container: Container) -> None:
    budgets = await container.list_budgets.execute(message.from_user.id)
    if not budgets:
        await message.answer(
            "🎯 Бюджеты не установлены.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="➕ Создать бюджет", callback_data="budget_new")]]
            ),
        )
        return
    await message.answer(
        "🎯 <b>Ваши бюджеты:</b>\n<i>(нажмите для удаления)</i>",
        parse_mode="HTML",
        reply_markup=budgets_keyboard(budgets),
    )


@router.callback_query(F.data == "budget_new")
async def start_budget(callback: CallbackQuery, state: FSMContext, container: Container) -> None:
    cats = await container.list_categories.execute(callback.from_user.id, category_type="expense")
    await state.set_state(BudgetStates.waiting_for_category)
    builder = InlineKeyboardBuilder()
    for cat in cats:
        builder.button(text=f"{cat.icon or ''} {cat.name}".strip(), callback_data=f"bcat:{cat.id}")
    builder.button(text="📊 Все расходы", callback_data="bcat:0")
    builder.adjust(2)
    await callback.message.edit_text(
        "Выберите категорию для бюджета:", reply_markup=builder.as_markup()
    )
    await callback.answer()


@router.callback_query(BudgetStates.waiting_for_category, F.data.startswith("bcat:"))
async def budget_cat_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    cat_id = callback.data.split(":")[1]
    await state.update_data(category_id=int(cat_id) if cat_id != "0" else None)
    await state.set_state(BudgetStates.waiting_for_limit)
    await callback.message.edit_text("Введите лимит суммы:")
    await callback.answer()


@router.message(BudgetStates.waiting_for_limit)
async def budget_limit_entered(message: Message, state: FSMContext) -> None:
    try:
        v = Decimal(message.text.strip().replace(",", "."))
        assert v > 0
    except Exception:
        await message.answer("Неверная сумма.")
        return
    await state.update_data(limit=str(v))
    await state.set_state(BudgetStates.waiting_for_period)
    await message.answer("Выберите период:", reply_markup=budget_period_keyboard())


@router.callback_query(BudgetStates.waiting_for_period, F.data.startswith("budget_period:"))
async def budget_period_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    period = callback.data.split(":")[1]
    await state.update_data(period=period)
    data = await state.get_data()
    await state.set_state(BudgetStates.confirming)
    await callback.message.edit_text(
        f"📋 <b>Новый бюджет:</b>\n\n"
        f"Категория: {data.get('category_id') or 'Все расходы'}\n"
        f"Лимит: <b>{Decimal(data['limit']):,.2f}</b>\n"
        f"Период: {PERIOD_LABELS.get(period, period)}",
        parse_mode="HTML",
        reply_markup=confirm_keyboard("budget_confirm", "cancel"),
    )
    await callback.answer()


@router.callback_query(BudgetStates.confirming, F.data == "budget_confirm")
async def budget_confirmed(callback: CallbackQuery, state: FSMContext, container: Container) -> None:
    data = await state.get_data()
    await container.set_budget.execute(
        user_id=callback.from_user.id,
        limit_amount=Decimal(data["limit"]),
        period=BudgetPeriod(data["period"]),
        category_id=data.get("category_id"),
    )
    await state.clear()
    await callback.message.edit_text("✅ Бюджет установлен!")
    await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("budget_del:"))
async def delete_budget(callback: CallbackQuery, container: Container) -> None:
    budget_id = int(callback.data.split(":")[1])
    await container.delete_budget.execute(budget_id, callback.from_user.id)
    await callback.answer("🗑 Бюджет удалён", show_alert=True)
    await callback.message.delete()
