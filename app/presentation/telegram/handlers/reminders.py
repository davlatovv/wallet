from datetime import date
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton

from app.application.dto.reminder import (
    CreateCreditReminderDTO,
    CreateInstallmentReminderDTO,
    CreateEducationReminderDTO,
    CreateRegularReminderDTO,
    ReminderDetailDTO,
)
from app.domain.entities.reminder import ReminderType, PaymentType, ReminderStatus
from app.domain.exceptions.base import NotFoundError
from app.infrastructure.container import Container
from app.presentation.telegram.keyboards.main_menu import main_menu_keyboard
from app.presentation.telegram.keyboards.reminders import (
    reminder_type_keyboard,
    credit_payment_type_keyboard,
    reminders_list_keyboard,
    reminder_detail_keyboard,
    confirm_payment_keyboard,
    TYPE_LABELS,
)
from app.presentation.telegram.states.reminder import ReminderStates

router = Router(name="reminders")

PAYMENT_TYPE_LABELS = {
    "annuity": "Аннуитетный",
    "differential": "Дифференциальный",
}


# ─── Helpers ──────────────────────────────────────────────────────────────────

def _format_reminder_card(r: ReminderDetailDTO) -> str:
    type_label = TYPE_LABELS.get(r.reminder_type, "🔔")
    lines = [f"{type_label}: <b>{r.name}</b>"]

    if r.reminder_type == ReminderType.CREDIT and r.interest_rate is not None and r.payment_type is not None:
        pt = PAYMENT_TYPE_LABELS.get(r.payment_type.value, r.payment_type.value)
        lines.append(f"Тип: {pt}, {r.interest_rate}% годовых")

    if r.total_amount is not None:
        lines.append(f"Общая сумма: <b>{r.total_amount:,.2f}</b>")

    lines.append(f"Оплачено: <b>{r.paid_amount:,.2f}</b>")

    if r.months_total is not None:
        lines.append(f"Периодов: {r.months_paid}/{r.months_total} мес.")

    if r.remaining_amount is not None:
        lines.append(f"Остаток: <b>{r.remaining_amount:,.2f}</b>")

    if r.progress_percent is not None:
        bar_filled = r.progress_percent // 10
        bar = "█" * bar_filled + "░" * (10 - bar_filled)
        lines.append(f"Прогресс: [{bar}] {r.progress_percent}%")

    if r.status == ReminderStatus.ACTIVE:
        lines.append(f"\n📅 Следующий платёж: <b>{r.next_payment_date.strftime('%d.%m.%Y')}</b>")
        lines.append(f"💰 Сумма платежа: <b>{r.payment_amount:,.2f}</b>")
    else:
        lines.append("\n✅ <b>Полностью оплачено</b>")

    return "\n".join(lines)


async def _show_reminders_list(target: Message | CallbackQuery, container: Container) -> None:
    user_id = target.from_user.id
    reminders = await container.list_reminders.execute(user_id)

    if not reminders:
        kb = InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="➕ Добавить", callback_data="rem_new")]]
        )
        text = "🔔 <b>Регулярные платежи</b>\n\nУ вас нет активных напоминаний."
        if isinstance(target, Message):
            await target.answer(text, parse_mode="HTML", reply_markup=kb)
        else:
            await target.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
        return

    active = [r for r in reminders if r.status == ReminderStatus.ACTIVE]
    completed = [r for r in reminders if r.status == ReminderStatus.COMPLETED]

    summary_lines = [f"🔔 <b>Регулярные платежи</b>"]
    if active:
        summary_lines.append(f"Активных: <b>{len(active)}</b>")
        total_month = sum(r.payment_amount for r in active)
        summary_lines.append(f"В этом месяце: <b>{total_month:,.2f}</b>")
    if completed:
        summary_lines.append(f"Завершённых: {len(completed)}")

    text = "\n".join(summary_lines)
    if isinstance(target, Message):
        await target.answer(text, parse_mode="HTML", reply_markup=reminders_list_keyboard(reminders))
    else:
        await target.message.edit_text(text, parse_mode="HTML", reply_markup=reminders_list_keyboard(reminders))


# ─── Entry point ──────────────────────────────────────────────────────────────

@router.message(F.text == "🔔 Регулярные платежи")
async def reminders_menu(message: Message, container: Container) -> None:
    await _show_reminders_list(message, container)


@router.callback_query(F.data == "rem_list")
async def reminders_list_cb(callback: CallbackQuery, container: Container) -> None:
    await _show_reminders_list(callback, container)
    await callback.answer()


@router.callback_query(F.data == "rem_back")
async def reminders_back(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text(
        "🔔 Регулярные платежи",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="➕ Добавить", callback_data="rem_new")]]
        ),
    )
    await callback.answer()


# ─── Detail view ──────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("rem_detail:"))
async def reminder_detail(callback: CallbackQuery, container: Container) -> None:
    reminder_id = int(callback.data.split(":")[1])
    try:
        r = await container.get_reminder_detail.execute(reminder_id, callback.from_user.id)
    except NotFoundError:
        await callback.answer("Напоминание не найдено", show_alert=True)
        return
    text = _format_reminder_card(r)
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=reminder_detail_keyboard(r.id, r.status == ReminderStatus.COMPLETED),
    )
    await callback.answer()


# ─── Payment schedule ─────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("rem_schedule:"))
async def reminder_schedule(callback: CallbackQuery, container: Container) -> None:
    reminder_id = int(callback.data.split(":")[1])
    try:
        r = await container.get_reminder_detail.execute(reminder_id, callback.from_user.id)
    except NotFoundError:
        await callback.answer("Напоминание не найдено", show_alert=True)
        return

    if r.reminder_type != ReminderType.CREDIT or not r.payment_schedule:
        await callback.answer("График доступен только для кредитов", show_alert=True)
        return

    lines = [f"📅 <b>График: {r.name}</b>\n"]
    for item in r.payment_schedule[:24]:  # показываем максимум 24 месяца
        paid_mark = "✅" if item["month"] <= r.months_paid else "  "
        lines.append(
            f"{paid_mark} <b>Мес.{item['month']:02d}</b>: "
            f"{item['payment']:,.0f} "
            f"(осн: {item['principal_part']:,.0f}, "
            f"%: {item['interest_part']:,.0f}), "
            f"ост: {item['balance']:,.0f}"
        )

    text = "\n".join(lines)
    # Telegram limit is 4096, trim if needed
    if len(text) > 4000:
        text = text[:4000] + "\n..."

    kb = InlineKeyboardMarkup(
        inline_keyboard=[[InlineKeyboardButton(text="◀️ Назад", callback_data=f"rem_detail:{reminder_id}")]]
    )
    await callback.message.edit_text(text, parse_mode="HTML", reply_markup=kb)
    await callback.answer()


# ─── Record payment ───────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("rem_pay:"))
async def record_payment_start(callback: CallbackQuery, container: Container) -> None:
    reminder_id = int(callback.data.split(":")[1])
    try:
        r = await container.get_reminder_detail.execute(reminder_id, callback.from_user.id)
    except NotFoundError:
        await callback.answer("Напоминание не найдено", show_alert=True)
        return

    text = (
        f"✅ Записать платёж\n\n"
        f"<b>{r.name}</b>\n"
        f"Сумма: <b>{r.payment_amount:,.2f}</b>\n"
        f"Дата: {r.next_payment_date.strftime('%d.%m.%Y')}"
    )
    await callback.message.edit_text(
        text,
        parse_mode="HTML",
        reply_markup=confirm_payment_keyboard(reminder_id),
    )
    await callback.answer()


@router.callback_query(F.data.startswith("rem_pay_confirm:"))
async def record_payment_confirm(callback: CallbackQuery, container: Container) -> None:
    reminder_id = int(callback.data.split(":")[1])
    try:
        r = await container.record_payment.execute(reminder_id, callback.from_user.id)
    except NotFoundError:
        await callback.answer("Напоминание не найдено", show_alert=True)
        return

    completed_msg = "\n\n🎉 <b>Полностью оплачено!</b>" if r.status == ReminderStatus.COMPLETED else ""
    next_msg = f"\n📅 Следующий платёж: {r.next_payment_date.strftime('%d.%m.%Y')}" if r.status == ReminderStatus.ACTIVE else ""
    await callback.message.edit_text(
        f"✅ Платёж <b>{r.payment_amount:,.2f}</b> записан!\n"
        f"Оплачено всего: {r.paid_amount:,.2f}"
        f"{next_msg}{completed_msg}",
        parse_mode="HTML",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[[InlineKeyboardButton(text="◀️ К списку", callback_data="rem_list")]]
        ),
    )
    await callback.answer()


# ─── Delete ───────────────────────────────────────────────────────────────────

@router.callback_query(F.data.startswith("rem_delete:"))
async def delete_reminder(callback: CallbackQuery, container: Container) -> None:
    reminder_id = int(callback.data.split(":")[1])
    try:
        await container.delete_reminder.execute(reminder_id, callback.from_user.id)
    except NotFoundError:
        await callback.answer("Напоминание не найдено", show_alert=True)
        return
    await callback.message.edit_text("🗑 Напоминание удалено.")
    await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()


# ─── Add new reminder ─────────────────────────────────────────────────────────

@router.callback_query(F.data == "rem_new")
async def start_new_reminder(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(ReminderStates.choosing_type)
    await callback.message.edit_text(
        "Выберите тип напоминания:",
        reply_markup=reminder_type_keyboard(),
    )
    await callback.answer()


@router.callback_query(ReminderStates.choosing_type, F.data.startswith("rem_type:"))
async def reminder_type_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    rtype = callback.data.split(":")[1]
    await state.update_data(reminder_type=rtype)
    await state.set_state(ReminderStates.waiting_for_name)
    type_label = {
        "credit": "кредита",
        "installment": "рассрочки",
        "education": "контракта",
        "regular": "расхода",
    }.get(rtype, "напоминания")
    await callback.message.edit_text(f"Введите название {type_label}:")
    await callback.answer()


# ─── Name (common) ────────────────────────────────────────────────────────────

@router.message(ReminderStates.waiting_for_name)
async def reminder_name_entered(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    data = await state.get_data()
    rtype = data["reminder_type"]

    if rtype == "credit":
        await state.set_state(ReminderStates.credit_total)
        await message.answer("Общая сумма кредита:")
    elif rtype == "installment":
        await state.set_state(ReminderStates.inst_total)
        await message.answer("Общая сумма рассрочки:")
    elif rtype == "education":
        await state.set_state(ReminderStates.edu_total)
        await message.answer("Общая сумма контракта:")
    else:  # regular
        await state.set_state(ReminderStates.edu_payment)
        await message.answer("Сумма ежемесячного расхода:")


# ─── CREDIT flow ──────────────────────────────────────────────────────────────

@router.message(ReminderStates.credit_total)
async def credit_total_entered(message: Message, state: FSMContext) -> None:
    try:
        v = Decimal(message.text.strip().replace(",", "."))
        assert v > 0
    except Exception:
        await message.answer("Неверная сумма. Введите положительное число:")
        return
    await state.update_data(total=str(v))
    await state.set_state(ReminderStates.credit_rate)
    await message.answer("Годовой процент (например: 18.5):")


@router.message(ReminderStates.credit_rate)
async def credit_rate_entered(message: Message, state: FSMContext) -> None:
    try:
        v = Decimal(message.text.strip().replace(",", "."))
        assert v >= 0
    except Exception:
        await message.answer("Неверное значение. Введите процент (например: 18.5):")
        return
    await state.update_data(rate=str(v))
    await state.set_state(ReminderStates.credit_months)
    await message.answer("Количество месяцев:")


@router.message(ReminderStates.credit_months)
async def credit_months_entered(message: Message, state: FSMContext) -> None:
    try:
        v = int(message.text.strip())
        assert v >= 1
    except Exception:
        await message.answer("Введите целое число >= 1:")
        return
    await state.update_data(months=v)
    await state.set_state(ReminderStates.credit_payment_type)
    await message.answer("Тип платежа:", reply_markup=credit_payment_type_keyboard())


@router.callback_query(ReminderStates.credit_payment_type, F.data.startswith("rem_ptype:"))
async def credit_payment_type_chosen(callback: CallbackQuery, state: FSMContext) -> None:
    ptype = callback.data.split(":")[1]
    await state.update_data(payment_type=ptype)
    await state.set_state(ReminderStates.waiting_for_payment_day)
    await callback.message.edit_text("День месяца для оплаты (1–31):")
    await callback.answer()


# ─── INSTALLMENT flow ─────────────────────────────────────────────────────────

@router.message(ReminderStates.inst_total)
async def inst_total_entered(message: Message, state: FSMContext) -> None:
    try:
        v = Decimal(message.text.strip().replace(",", "."))
        assert v > 0
    except Exception:
        await message.answer("Неверная сумма:")
        return
    await state.update_data(total=str(v))
    await state.set_state(ReminderStates.inst_monthly)
    await message.answer("Ежемесячный платёж:")


@router.message(ReminderStates.inst_monthly)
async def inst_monthly_entered(message: Message, state: FSMContext) -> None:
    try:
        v = Decimal(message.text.strip().replace(",", "."))
        assert v > 0
    except Exception:
        await message.answer("Неверная сумма:")
        return
    await state.update_data(monthly=str(v))
    await state.set_state(ReminderStates.inst_months)
    await message.answer("Количество месяцев:")


@router.message(ReminderStates.inst_months)
async def inst_months_entered(message: Message, state: FSMContext) -> None:
    try:
        v = int(message.text.strip())
        assert v >= 1
    except Exception:
        await message.answer("Введите целое число >= 1:")
        return
    await state.update_data(months=v)
    await state.set_state(ReminderStates.waiting_for_payment_day)
    await message.answer("День месяца для оплаты (1–31):")


# ─── EDUCATION flow ───────────────────────────────────────────────────────────

@router.message(ReminderStates.edu_total)
async def edu_total_entered(message: Message, state: FSMContext) -> None:
    try:
        v = Decimal(message.text.strip().replace(",", "."))
        assert v > 0
    except Exception:
        await message.answer("Неверная сумма:")
        return
    await state.update_data(total=str(v))
    await state.set_state(ReminderStates.edu_payment)
    await message.answer("Сумма одного платежа:")


@router.message(ReminderStates.edu_payment)
async def edu_payment_entered(message: Message, state: FSMContext) -> None:
    try:
        v = Decimal(message.text.strip().replace(",", "."))
        assert v > 0
    except Exception:
        await message.answer("Неверная сумма:")
        return
    await state.update_data(payment=str(v))
    await state.set_state(ReminderStates.waiting_for_payment_day)
    await message.answer("День месяца для оплаты (1–31):")


# ─── Payment day + first date (common tail) ───────────────────────────────────

@router.message(ReminderStates.waiting_for_payment_day)
async def payment_day_entered(message: Message, state: FSMContext) -> None:
    try:
        v = int(message.text.strip())
        assert 1 <= v <= 31
    except Exception:
        await message.answer("Введите число от 1 до 31:")
        return
    await state.update_data(payment_day=v)
    await state.set_state(ReminderStates.waiting_for_first_date)
    await message.answer("Дата первого платежа (ДД.ММ.ГГГГ):")


@router.message(ReminderStates.waiting_for_first_date)
async def first_date_entered(message: Message, state: FSMContext) -> None:
    text = message.text.strip()
    try:
        # Accept both DD.MM.YYYY and YYYY-MM-DD
        if "." in text:
            parts = text.split(".")
            first_date = date(int(parts[2]), int(parts[1]), int(parts[0]))
        else:
            first_date = date.fromisoformat(text)
    except Exception:
        await message.answer("Неверный формат. Введите дату как ДД.ММ.ГГГГ:")
        return

    await state.update_data(first_date=str(first_date))
    data = await state.get_data()
    rtype = data["reminder_type"]

    # Build confirmation text
    await _show_confirmation(message, state, data, rtype, first_date)


async def _show_confirmation(
    message: Message,
    state: FSMContext,
    data: dict,
    rtype: str,
    first_date: date,
) -> None:
    from app.presentation.telegram.keyboards.inline import confirm_keyboard

    if rtype == "credit":
        ptype_label = PAYMENT_TYPE_LABELS.get(data.get("payment_type", "annuity"), "")
        # Calculate first payment for preview
        from app.domain.value_objects.credit_calculator import CreditCalculator
        from app.domain.entities.reminder import PaymentType as PT
        principal = Decimal(data["total"])
        rate = Decimal(data["rate"])
        months = data["months"]
        pt = data.get("payment_type", "annuity")
        if pt == "annuity":
            pmt = CreditCalculator.annuity_payment(principal, rate, months)
        else:
            pmt = CreditCalculator.differential_payment(principal, rate, months, 1)

        text = (
            f"📋 <b>Кредит:</b>\n\n"
            f"Название: <b>{data['name']}</b>\n"
            f"Сумма: <b>{principal:,.2f}</b>\n"
            f"Ставка: <b>{rate}%</b> годовых\n"
            f"Месяцев: <b>{months}</b>\n"
            f"Тип: <b>{ptype_label}</b>\n"
            f"1-й платёж: <b>{pmt:,.2f}</b>\n"
            f"День оплаты: {data['payment_day']}-е\n"
            f"Дата первого платежа: {first_date.strftime('%d.%m.%Y')}"
        )
        await state.set_state(ReminderStates.credit_confirming)

    elif rtype == "installment":
        text = (
            f"📋 <b>Рассрочка:</b>\n\n"
            f"Название: <b>{data['name']}</b>\n"
            f"Общая сумма: <b>{Decimal(data['total']):,.2f}</b>\n"
            f"Платёж: <b>{Decimal(data['monthly']):,.2f}</b>/мес\n"
            f"Месяцев: <b>{data['months']}</b>\n"
            f"День оплаты: {data['payment_day']}-е\n"
            f"Дата первого платежа: {first_date.strftime('%d.%m.%Y')}"
        )
        await state.set_state(ReminderStates.inst_confirming)

    elif rtype == "education":
        text = (
            f"📋 <b>Контракт за учёбу:</b>\n\n"
            f"Название: <b>{data['name']}</b>\n"
            f"Общая сумма: <b>{Decimal(data['total']):,.2f}</b>\n"
            f"Платёж: <b>{Decimal(data['payment']):,.2f}</b>\n"
            f"День оплаты: {data['payment_day']}-е\n"
            f"Дата первого платежа: {first_date.strftime('%d.%m.%Y')}"
        )
        await state.set_state(ReminderStates.edu_confirming)

    else:  # regular
        text = (
            f"📋 <b>Постоянный расход:</b>\n\n"
            f"Название: <b>{data['name']}</b>\n"
            f"Платёж: <b>{Decimal(data['payment']):,.2f}</b>\n"
            f"День оплаты: {data['payment_day']}-е\n"
            f"Дата первого платежа: {first_date.strftime('%d.%m.%Y')}"
        )
        await state.set_state(ReminderStates.edu_confirming)

    from app.presentation.telegram.keyboards.inline import confirm_keyboard
    await message.answer(text, parse_mode="HTML", reply_markup=confirm_keyboard("rem_confirm", "rem_cancel"))


# ─── Confirm ──────────────────────────────────────────────────────────────────

@router.callback_query(
    F.data == "rem_confirm",
    ReminderStates.credit_confirming,
)
async def credit_confirmed(callback: CallbackQuery, state: FSMContext, container: Container) -> None:
    data = await state.get_data()
    dto = CreateCreditReminderDTO(
        name=data["name"],
        total_amount=Decimal(data["total"]),
        interest_rate=Decimal(data["rate"]),
        months_total=data["months"],
        payment_type=PaymentType(data["payment_type"]),
        payment_day=data["payment_day"],
        first_payment_date=date.fromisoformat(data["first_date"]),
    )
    result = await container.create_credit_reminder.execute(callback.from_user.id, dto)
    await state.clear()
    await callback.message.edit_text(
        f"✅ Кредит <b>{result.name}</b> добавлен!\n"
        f"Первый платёж: <b>{result.payment_amount:,.2f}</b>\n"
        f"Дата: {result.next_payment_date.strftime('%d.%m.%Y')}\n"
        f"🔔 Напоминание включено — уведомление придёт в 08:00 в день оплаты.",
        parse_mode="HTML",
    )
    await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(
    F.data == "rem_confirm",
    ReminderStates.inst_confirming,
)
async def installment_confirmed(callback: CallbackQuery, state: FSMContext, container: Container) -> None:
    data = await state.get_data()
    dto = CreateInstallmentReminderDTO(
        name=data["name"],
        total_amount=Decimal(data["total"]),
        monthly_payment=Decimal(data["monthly"]),
        months_total=data["months"],
        payment_day=data["payment_day"],
        first_payment_date=date.fromisoformat(data["first_date"]),
    )
    result = await container.create_installment_reminder.execute(callback.from_user.id, dto)
    await state.clear()
    await callback.message.edit_text(
        f"✅ Рассрочка <b>{result.name}</b> добавлена!\n"
        f"Платёж: <b>{result.payment_amount:,.2f}</b>/мес\n"
        f"Дата: {result.next_payment_date.strftime('%d.%m.%Y')}\n"
        f"🔔 Напоминание включено.",
        parse_mode="HTML",
    )
    await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(
    F.data == "rem_confirm",
    ReminderStates.edu_confirming,
)
async def edu_or_regular_confirmed(callback: CallbackQuery, state: FSMContext, container: Container) -> None:
    data = await state.get_data()
    rtype = data["reminder_type"]
    first_date = date.fromisoformat(data["first_date"])

    if rtype == "education":
        dto = CreateEducationReminderDTO(
            name=data["name"],
            total_amount=Decimal(data["total"]),
            payment_amount=Decimal(data["payment"]),
            payment_day=data["payment_day"],
            first_payment_date=first_date,
        )
        result = await container.create_education_reminder.execute(callback.from_user.id, dto)
        label = "Контракт"
    else:
        dto = CreateRegularReminderDTO(
            name=data["name"],
            payment_amount=Decimal(data["payment"]),
            payment_day=data["payment_day"],
            first_payment_date=first_date,
        )
        result = await container.create_regular_reminder.execute(callback.from_user.id, dto)
        label = "Расход"

    await state.clear()
    await callback.message.edit_text(
        f"✅ {label} <b>{result.name}</b> добавлен!\n"
        f"Платёж: <b>{result.payment_amount:,.2f}</b>\n"
        f"Дата: {result.next_payment_date.strftime('%d.%m.%Y')}\n"
        f"🔔 Напоминание включено.",
        parse_mode="HTML",
    )
    await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data == "rem_cancel")
async def reminder_cancel(callback: CallbackQuery, state: FSMContext) -> None:
    await state.clear()
    await callback.message.edit_text("❌ Добавление отменено.")
    await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()
