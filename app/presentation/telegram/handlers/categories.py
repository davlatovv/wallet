from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.infrastructure.container import Container
from app.presentation.telegram.keyboards.main_menu import main_menu_keyboard

router = Router(name="categories")


def categories_manage_keyboard(categories, cat_type: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in categories:
        icon = cat.icon or ""
        label = f"{icon} {cat.name}".strip()
        builder.button(text=label, callback_data=f"cat_view:{cat.id}")
    builder.button(text="➕ Добавить категорию", callback_data=f"cat_add:{cat_type}")
    builder.adjust(2)
    return builder.as_markup()


@router.message(F.text == "📂 Категории")
async def categories_menu(message: Message, container: Container) -> None:
    expense_cats = await container.list_categories.execute(message.from_user.id, category_type="expense")
    income_cats = await container.list_categories.execute(message.from_user.id, category_type="income")

    exp_names = ", ".join(f"{c.icon or ''}{c.name}" for c in expense_cats[:5])
    inc_names = ", ".join(f"{c.icon or ''}{c.name}" for c in income_cats[:5])

    await message.answer(
        f"📂 <b>Категории</b>\n\n"
        f"📤 Расходы ({len(expense_cats)}): {exp_names or '—'}\n"
        f"📥 Доходы ({len(income_cats)}): {inc_names or '—'}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📤 Расходы", callback_data="cat_list:expense"),
                    InlineKeyboardButton(text="📥 Доходы", callback_data="cat_list:income"),
                ]
            ]
        ),
    )


@router.callback_query(F.data.startswith("cat_list:"))
async def category_list(callback: CallbackQuery, container: Container) -> None:
    cat_type = callback.data.split(":")[1]
    cats = await container.list_categories.execute(callback.from_user.id, category_type=cat_type)
    label = "Расходы" if cat_type == "expense" else "Доходы"
    await callback.message.edit_text(
        f"📂 <b>Категории: {label}</b>",
        parse_mode="HTML",
        reply_markup=categories_manage_keyboard(cats, cat_type),
    )
    await callback.answer()
