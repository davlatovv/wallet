import logging

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from aiogram import Bot

logger = logging.getLogger(__name__)


async def daily_reminder(bot: Bot, chat_id: int) -> None:
    await bot.send_message(
        chat_id,
        "💡 <b>Напоминание</b>\n\nНе забудьте внести сегодняшние расходы!",
        parse_mode="HTML",
    )


def setup_scheduler(bot: Bot, user_id: int) -> AsyncIOScheduler:
    scheduler = AsyncIOScheduler()
    scheduler.add_job(
        daily_reminder,
        CronTrigger(hour=21, minute=0),
        args=[bot, user_id],
        id="daily_reminder",
        replace_existing=True,
    )
    logger.info("Scheduler configured for user %d", user_id)
    return scheduler
