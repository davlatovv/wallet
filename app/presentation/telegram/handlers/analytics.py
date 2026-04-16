from aiogram import Router, F
from aiogram.types import Message, CallbackQuery

from app.application.use_cases.analytics.get_report import ReportPeriod
from app.infrastructure.container import Container
from app.presentation.telegram.keyboards.inline import period_keyboard

router = Router(name="analytics")

PERIOD_LABELS = {
    ReportPeriod.DAY: "сегодня",
    ReportPeriod.WEEK: "эта неделя",
    ReportPeriod.MONTH: "этот месяц",
}


def _format_report(result) -> str:
    label = PERIOD_LABELS.get(result.period, result.period.value)
    lines = [
        f"📊 <b>Отчёт: {label}</b>\n",
        f"📥 Доходы:  <b>{result.total_income:,.2f}</b>",
        f"📤 Расходы: <b>{result.total_expense:,.2f}</b>",
    ]
    if result.total_savings > 0:
        lines.append(f"🏦 Копилка: <b>{result.total_savings:,.2f}</b>")
    sign = "+" if result.balance >= 0 else ""
    lines.append(f"💼 Итого:   <b>{sign}{result.balance:,.2f}</b>")

    if result.expense_by_category:
        lines.append("\n<b>Расходы по категориям:</b>")
        for cat in result.expense_by_category[:7]:
            lines.append(f"  {cat.category_name}: {cat.amount:,.2f} ({cat.percent}%)")

    if result.total_savings > 0:
        lines.append("\n<b>Накоплено в копилку за период:</b>")
        lines.append(f"  🏦 {result.total_savings:,.2f}")

    return "\n".join(lines)


@router.message(F.text == "📊 Статистика")
async def handle_analytics_menu(message: Message) -> None:
    await message.answer("Выберите период:", reply_markup=period_keyboard())


@router.callback_query(F.data.startswith("report:"))
async def handle_report(callback: CallbackQuery, container: Container) -> None:
    period_str = callback.data.split(":")[1]
    period = ReportPeriod(period_str)
    result = await container.get_report.execute(callback.from_user.id, period)
    await callback.message.edit_text(_format_report(result), parse_mode="HTML")
    await callback.answer()
