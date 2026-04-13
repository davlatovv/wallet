from datetime import date
from decimal import Decimal, InvalidOperation

from aiogram import Router, F
from aiogram.fsm.context import FSMContext
from aiogram.types import Message, CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.utils.keyboard import InlineKeyboardBuilder

from app.domain.entities.installment import InstallmentStatus
from app.infrastructure.container import Container
from app.presentation.telegram.keyboards.inline import confirm_keyboard
from app.presentation.telegram.keyboards.main_menu import main_menu_keyboard
from app.presentation.telegram.states.installment import InstallmentStates

router = Router(name="installments")


def installments_keyboard(insts) -> InlineKeyboardMarkup:
    builder = InlineKeyboardBuilder()
    for i in insts:
        label = f"{i.name} ({i.months_paid}/{i.months_total})"
        builder.button(text=label, callback_data=f"inst_pay:{i.id}")
    builder.button(text="➕ Добавить рассрочку", callback_data="inst_new")
    builder.adjust(1)
    return builder.as_markup()


def _format_installment(i) -> str:
    nd = f"\n📅 Следующий платёж: {i.next_payment_date}" if i.next_payment_date else ""
    return (
        f"📆 <b>{i.name}</b>\n"
        f"Платёж: {i.monthly_payment:,.2f} × {i.months_total} мес.\n"
        f"Оплачено: {i.months_paid}/{i.months_total} ({i.amount_paid:,.2f})\n"
        f"Остаток: {i.amount_remaining:,.2f}{nd}"
    )


@router.message(F.text == "📆 Рассрочки")
async def installments_menu(message: Message, container: Container) -> None:
    insts = await container.list_installments.execute(message.from_user.id)
    active = [i for i in insts if i.status == InstallmentStatus.ACTIVE]
    if not active:
        await message.answer(
            "📆 Активных рассрочек нет.",
            reply_markup=InlineKeyboardMarkup(
                inline_keyboard=[[InlineKeyboardButton(text="➕ Добавить", callback_data="inst_new")]]
            ),
        )
        return
    text = "\n\n".join(_format_installment(i) for i in active)
    await message.answer(text, parse_mode="HTML", reply_markup=installments_keyboard(active))


@router.callback_query(F.data == "inst_new")
async def start_new_installment(callback: CallbackQuery, state: FSMContext) -> None:
    await state.set_state(InstallmentStates.waiting_for_name)
    await callback.message.edit_text("Введите название рассрочки (например: iPhone 15):")
    await callback.answer()


@router.message(InstallmentStates.waiting_for_name)
async def inst_name_entered(message: Message, state: FSMContext) -> None:
    await state.update_data(name=message.text.strip())
    await state.set_state(InstallmentStates.waiting_for_total)
    await message.answer("Общая сумма:")


@router.message(InstallmentStates.waiting_for_total)
async def inst_total_entered(message: Message, state: FSMContext) -> None:
    try:
        v = Decimal(message.text.strip().replace(",", "."))
        assert v > 0
    except Exception:
        await message.answer("Неверная сумма.")
        return
    await state.update_data(total=str(v))
    await state.set_state(InstallmentStates.waiting_for_monthly)
    await message.answer("Ежемесячный платёж:")


@router.message(InstallmentStates.waiting_for_monthly)
async def inst_monthly_entered(message: Message, state: FSMContext) -> None:
    try:
        v = Decimal(message.text.strip().replace(",", "."))
        assert v > 0
    except Exception:
        await message.answer("Неверная сумма.")
        return
    await state.update_data(monthly=str(v))
    await state.set_state(InstallmentStates.waiting_for_months)
    await message.answer("Количество месяцев:")


@router.message(InstallmentStates.waiting_for_months)
async def inst_months_entered(message: Message, state: FSMContext) -> None:
    try:
        v = int(message.text.strip())
        assert v >= 1
    except Exception:
        await message.answer("Введите целое число >= 1.")
        return
    await state.update_data(months=v)
    await state.set_state(InstallmentStates.waiting_for_first_payment)
    await message.answer("Дата первого платежа (ГГГГ-ММ-ДД) или /skip:")


@router.message(InstallmentStates.waiting_for_first_payment, F.text == "/skip")
@router.message(InstallmentStates.waiting_for_first_payment)
async def inst_first_payment_entered(message: Message, state: FSMContext) -> None:
    date_str = None
    if message.text != "/skip":
        try:
            date_str = str(date.fromisoformat(message.text.strip()))
        except ValueError:
            await message.answer("Неверный формат. ГГГГ-ММ-ДД или /skip.")
            return
    await state.update_data(first_payment=date_str)
    data = await state.get_data()
    await state.set_state(InstallmentStates.confirming)
    await message.answer(
        f"📋 <b>Рассрочка:</b>\n\n"
        f"Название: <b>{data['name']}</b>\n"
        f"Итого: <b>{Decimal(data['total']):,.2f}</b>\n"
        f"Платёж: <b>{Decimal(data['monthly']):,.2f}</b>/мес × {data['months']} мес.\n"
        f"Первый платёж: {date_str or '—'}",
        parse_mode="HTML",
        reply_markup=confirm_keyboard("inst_confirm", "cancel"),
    )


@router.callback_query(InstallmentStates.confirming, F.data == "inst_confirm")
async def inst_confirmed(callback: CallbackQuery, state: FSMContext, container: Container) -> None:
    data = await state.get_data()
    fp = date.fromisoformat(data["first_payment"]) if data.get("first_payment") else None
    await container.add_installment.execute(
        user_id=callback.from_user.id,
        name=data["name"],
        total_amount=Decimal(data["total"]),
        monthly_payment=Decimal(data["monthly"]),
        months_total=data["months"],
        next_payment_date=fp,
    )
    await state.clear()
    await callback.message.edit_text(f"✅ Рассрочка <b>{data['name']}</b> добавлена!", parse_mode="HTML")
    await callback.message.answer("Главное меню:", reply_markup=main_menu_keyboard())
    await callback.answer()


@router.callback_query(F.data.startswith("inst_pay:"))
async def pay_installment(callback: CallbackQuery, container: Container) -> None:
    inst_id = int(callback.data.split(":")[1])
    inst = await container.pay_installment_month.execute(inst_id, callback.from_user.id)
    completed = " 🎉 Рассрочка завершена!" if inst.is_completed else ""
    await callback.answer(
        f"✅ Платёж {inst.months_paid}/{inst.months_total} записан!{completed}",
        show_alert=True,
    )
    await callback.message.delete()
