import logging
from datetime import date

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot
from sqlalchemy.ext.asyncio import async_sessionmaker

from app.infrastructure.db.repositories.reminder import SQLAlchemyReminderRepository

logger = logging.getLogger(__name__)

REMINDER_TYPE_LABELS = {
    "credit": "💳 Кредит",
    "installment": "📆 Рассрочка",
    "education": "📚 Контракт за учёбу",
    "regular": "🔄 Постоянный расход",
}


async def send_payment_reminders(bot: Bot, session_factory: async_sessionmaker) -> None:
    today = date.today()
    async with session_factory() as session:
        repo = SQLAlchemyReminderRepository(session)
        reminders = await repo.list_due_today(today)

    for reminder in reminders:
        type_label = REMINDER_TYPE_LABELS.get(reminder.reminder_type.value, "🔔 Платёж")
        progress = ""
        if reminder.months_total:
            progress = f"\nОплачено: {reminder.months_paid}/{reminder.months_total} мес."
        remaining = ""
        if reminder.remaining_amount is not None:
            remaining = f"\nОстаток: <b>{reminder.remaining_amount:,.2f}</b>"

        text = (
            f"🔔 <b>Напоминание об оплате</b>\n\n"
            f"{type_label}: <b>{reminder.name}</b>\n"
            f"Сумма: <b>{reminder.payment_amount:,.2f}</b>"
            f"{progress}"
            f"{remaining}\n\n"
            f"📅 Дата платежа: сегодня ({today.strftime('%d.%m.%Y')})"
        )
        try:
            await bot.send_message(reminder.user_id, text, parse_mode="HTML")
            logger.info(
                "Payment reminder sent: user=%d reminder=%d name=%s",
                reminder.user_id, reminder.id, reminder.name,
            )
        except Exception as exc:
            logger.warning(
                "Failed to send reminder to user=%d: %s", reminder.user_id, exc
            )


async def daily_generic_reminder(bot: Bot, chat_id: int) -> None:
    await bot.send_message(
        chat_id,
        "💡 <b>Напоминание</b>\n\nНе забудьте внести сегодняшние расходы!",
        parse_mode="HTML",
    )


def setup_scheduler(bot: Bot, session_factory: async_sessionmaker) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()

    # Payment reminders at 08:00 every day
    scheduler.add_job(
        send_payment_reminders,
        CronTrigger(hour=8, minute=0),
        args=[bot, session_factory],
        id="payment_reminders",
        replace_existing=True,
    )

    logger.info("Scheduler configured: payment reminders at 08:00 daily")
    return scheduler
