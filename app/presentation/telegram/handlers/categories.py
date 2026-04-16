from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.domain.exceptions.base import NotFoundError
from app.infrastructure.container import Container
from app.presentation.telegram.keyboards.main_menu import main_menu_keyboard
from app.presentation.telegram.states.category import CategoryStates

router = Router(name="categories")

TYPE_LABEL = {"expense": "Расходы", "income": "Доходы"}
TYPE_ICON = {"expense": "📤", "income": "📥"}


# ─── Keyboards ────────────────────────────────────────────────────────────────

def categories_list_keyboard(categories, cat_type: str) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for cat in categories:
        system_mark = " 🔒" if cat.is_system else ""
        label = f"{cat.icon or ''} {cat.name}{system_mark}".strip()
        builder.button(text=label, callback_data=f"cat_view:{cat.id}:{cat_type}")
    builder.adjust(2)
    builder.row(InlineKeyboardButton(text="➕ Добавить категорию", callback_data=f"cat_add:{cat_type}"))
    builder.row(InlineKeyboardButton(text="◀️ Назад", callback_data="cat_back"))
    return builder.as_markup()


def category_detail_keyboard(cat_id: int, cat_type: str, is_system: bool) -> InlineKeyboardMarkup:
    rows = []
    if not is_system:
        rows.append([
            InlineKeyboardButton(text="✏️ Переименовать", callback_data=f"cat_edit_name:{cat_id}:{cat_type}"),
            InlineKeyboardButton(text="🎨 Иконка", callback_data=f"cat_edit_icon:{cat_id}:{cat_type}"),
        ])
        rows.append([
            InlineKeyboardButton(text="🗑 Удалить", callback_data=f"cat_delete_ask:{cat_id}:{cat_type}"),
        ])
    else:
        rows.append([InlineKeyboardButton(text="🔒 Системная — редактирование недоступно", callback_data="noop_cat")])
    rows.append([InlineKeyboardButton(text="◀️ Назад", callback_data=f"cat_list:{cat_type}")])
    return InlineKeyboardMarkup(inline_keyboard=rows)


def confirm_delete_keyboard(cat_id: int, cat_type: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да, удалить", callback_data=f"cat_delete_confirm:{cat_id}:{cat_type}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"cat_view:{cat_id}:{cat_type}"),
            ]
        ]
    )


# ─── Overview ─────────────────────────────────────────────────────────────────

@router.message(F.text == "📂 Категории")
async def categories_menu(message: Message, container: Container) -> None:
    expense_cats = await container.list_categories.execute(message.from_user.id, category_type="expense")
    income_cats = await container.list_categories.execute(message.from_user.id, category_type="income")

    exp_names = ", ".join(f"{c.icon or ''}{c.name}" for c in expense_cats[:5])
    inc_names = ", ".join(f"{c.icon or ''}{c.name}" for c in income_cats[:5])
    exp_more = f" +{len(expense_cats) - 5} ещё" if len(expense_cats) > 5 else ""
    inc_more = f" +{len(income_cats) - 5} ещё" if len(income_cats) > 5 else ""

    await message.answer(
        f"📂 <b>Категории</b>\n\n"
        f"📤 Расходы ({len(expense_cats)}): {exp_names or '—'}{exp_more}\n"
        f"📥 Доходы ({len(income_cats)}): {inc_names or '—'}{inc_more}",
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


@router.callback_query(F.data == "cat_back")
async def categories_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "📂 <b>Категории</b>\n\nВыберите тип:",
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
    await callback.answer()


# ─── List ─────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cat_list:"))
async def category_list(callback: CallbackQuery, state: FSMContext, container: Container) -> None:
    await state.clear()
    cat_type = callback.data.split(":")[1]
    cats = await container.list_categories.execute(callback.from_user.id, category_type=cat_type)
    label = TYPE_LABEL.get(cat_type, cat_type)
    count = len(cats)
    await callback.message.edit_text(
        f"📂 <b>Категории: {label}</b> ({count})\n\nНажмите на категорию чтобы изменить или удалить.",
        parse_mode="HTML",
        reply_markup=categories_list_keyboard(cats, cat_type),
    )
    await callback.answer()


# ─── View single category ─────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cat_view:"))
async def category_view(callback: CallbackQuery, state: FSMContext, container: Container) -> None:
    await state.clear()
    parts = callback.data.split(":")
    cat_id, cat_type = int(parts[1]), parts[2]
    try:
        cat = await container.get_category.execute(cat_id, callback.from_user.id)
    except NotFoundError:
        await callback.answer("Категория не найдена", show_alert=True)
        return

    type_label = TYPE_LABEL.get(cat.category_type, cat.category_type)
    system_note = "\n🔒 <i>Системная категория — нельзя изменить</i>" if cat.is_system else ""
    text = (
        f"{cat.icon or '📁'} <b>{cat.name}</b>\n"
        f"Тип: {type_label}"
        f"{system_note}"
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=category_detail_keyboard(cat_id, cat_type, cat.is_system),
    )
    await callback.answer()


@router.callback_query(F.data == "noop_cat")
async def noop_cat(callback: CallbackQuery) -> None:
    await callback.answer()


# ─── Add ──────────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cat_add:"))
async def category_add_start(callback: CallbackQuery, state: FSMContext) -> None:
    cat_type = callback.data.split(":")[1]
    await state.update_data(cat_type=cat_type)
    await state.set_state(CategoryStates.adding_name)
    label = TYPE_LABEL.get(cat_type, cat_type).lower()
    await callback.message.edit_text(f"Введите название новой категории {label}:")
    await callback.answer()


@router.message(CategoryStates.adding_name)
async def category_add_name(message: Message, state: FSMContext) -> None:
    name = message.text.strip()
    if not name:
        await message.answer("Название не может быть пустым:")
        return
    await state.update_data(name=name)
    await state.set_state(CategoryStates.adding_icon)
    await message.answer(
        f"Введите эмодзи-иконку для категории <b>{name}</b> (или /skip):",
        parse_mode="HTML",
    )


@router.message(CategoryStates.adding_icon, F.text == "/skip")
@router.message(CategoryStates.adding_icon)
async def category_add_icon(message: Message, state: FSMContext, container: Container) -> None:
    icon = None if message.text == "/skip" else message.text.strip()
    data = await state.get_data()
    cat = await container.create_category.execute(
        user_id=message.from_user.id,
        name=data["name"],
        icon=icon,
        category_type=data["cat_type"],
    )
    await state.clear()
    type_label = TYPE_LABEL.get(cat.category_type, "").lower()
    await message.answer(
        f"✅ Категория {cat.icon or ''} <b>{cat.name}</b> добавлена в {type_label}!",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="📂 К списку", callback_data=f"cat_list:{cat.category_type}")
            ]]
        ),
    )


# ─── Edit name ────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cat_edit_name:"))
async def category_edit_name_start(callback: CallbackQuery, state: FSMContext, container: Container) -> None:
    parts = callback.data.split(":")
    cat_id, cat_type = int(parts[1]), parts[2]
    try:
        cat = await container.get_category.execute(cat_id, callback.from_user.id)
    except NotFoundError:
        await callback.answer("Категория не найдена", show_alert=True)
        return
    await state.update_data(cat_id=cat_id, cat_type=cat_type, current_icon=cat.icon)
    await state.set_state(CategoryStates.editing_name)
    await callback.message.edit_text(
        f"Текущее название: <b>{cat.name}</b>\n\nВведите новое название:",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(CategoryStates.editing_name)
async def category_edit_name_done(message: Message, state: FSMContext, container: Container) -> None:
    name = message.text.strip()
    if not name:
        await message.answer("Название не может быть пустым:")
        return
    data = await state.get_data()
    cat = await container.rename_category.execute(
        category_id=data["cat_id"],
        user_id=message.from_user.id,
        name=name,
        icon=data.get("current_icon"),
    )
    await state.clear()
    await message.answer(
        f"✅ Переименовано: {cat.icon or ''} <b>{cat.name}</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="◀️ К категории", callback_data=f"cat_view:{cat.id}:{data['cat_type']}")
            ]]
        ),
    )


# ─── Edit icon ────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cat_edit_icon:"))
async def category_edit_icon_start(callback: CallbackQuery, state: FSMContext, container: Container) -> None:
    parts = callback.data.split(":")
    cat_id, cat_type = int(parts[1]), parts[2]
    try:
        cat = await container.get_category.execute(cat_id, callback.from_user.id)
    except NotFoundError:
        await callback.answer("Категория не найдена", show_alert=True)
        return
    await state.update_data(cat_id=cat_id, cat_type=cat_type, current_name=cat.name)
    await state.set_state(CategoryStates.editing_icon)
    current = cat.icon or "нет"
    await callback.message.edit_text(
        f"Текущая иконка: <b>{current}</b>\n\nВведите новый эмодзи (или /skip чтобы убрать иконку):",
        parse_mode="HTML",
    )
    await callback.answer()


@router.message(CategoryStates.editing_icon, F.text == "/skip")
@router.message(CategoryStates.editing_icon)
async def category_edit_icon_done(message: Message, state: FSMContext, container: Container) -> None:
    icon = None if message.text == "/skip" else message.text.strip()
    data = await state.get_data()
    cat = await container.rename_category.execute(
        category_id=data["cat_id"],
        user_id=message.from_user.id,
        name=data["current_name"],
        icon=icon,
    )
    await state.clear()
    await message.answer(
        f"✅ Иконка обновлена: {cat.icon or '—'} <b>{cat.name}</b>",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[
                InlineKeyboardButton(text="◀️ К категории", callback_data=f"cat_view:{cat.id}:{data['cat_type']}")
            ]]
        ),
    )


# ─── Delete ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("cat_delete_ask:"))
async def category_delete_ask(callback: CallbackQuery, container: Container) -> None:
    parts = callback.data.split(":")
    cat_id, cat_type = int(parts[1]), parts[2]
    try:
        cat = await container.get_category.execute(cat_id, callback.from_user.id)
    except NotFoundError:
        await callback.answer("Категория не найдена", show_alert=True)
        return
    await callback.message.edit_text(
        f"🗑 Удалить категорию {cat.icon or ''} <b>{cat.name}</b>?\n\n"
        f"⚠️ Транзакции с этой категорией останутся, но потеряют привязку.",
        parse_mode="HTML",
        reply_markup=confirm_delete_keyboard(cat_id, cat_type),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("cat_delete_confirm:"))
async def category_delete_confirm(callback: CallbackQuery, container: Container) -> None:
    parts = callback.data.split(":")
    cat_id, cat_type = int(parts[1]), parts[2]
    try:
        await container.delete_category.execute(cat_id, callback.from_user.id)
    except NotFoundError:
        await callback.answer("Категория не найдена", show_alert=True)
        return
    cats = await container.list_categories.execute(callback.from_user.id, category_type=cat_type)
    label = TYPE_LABEL.get(cat_type, cat_type)
    await callback.message.edit_text(
        f"✅ Категория удалена.\n\n📂 <b>Категории: {label}</b> ({len(cats)})",
        parse_mode="HTML",
        reply_markup=categories_list_keyboard(cats, cat_type),
    )
    await callback.answer()
