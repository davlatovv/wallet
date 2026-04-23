import asyncio
import logging

import structlog
from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage

from app.config.settings import settings
from app.infrastructure.db.session.factory import async_session_factory, create_engine
from app.infrastructure.notifications.scheduler import setup_scheduler
from app.presentation.telegram.middlewares.db_session import DbSessionMiddleware
from app.presentation.telegram.middlewares.register_user import RegisterUserMiddleware
from app.presentation.telegram.router import main_router

logging.basicConfig(
    level=getattr(logging, settings.log_level.upper(), logging.INFO),
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
)
logger = logging.getLogger(__name__)


async def run_migrations(retries: int = 10, delay: float = 3.0) -> None:

    import subprocess, sys
    for attempt in range(1, retries + 1):
        logger.info("Applying migrations (attempt %d/%d)...", attempt, retries)
        result = subprocess.run(
            [sys.executable, "-m", "alembic", "upgrade", "head"],
            capture_output=True, text=True,
        )
        if result.returncode == 0:
            logger.info("Migrations applied.")
            return
        output = (result.stdout + result.stderr).strip()
        logger.warning("Migration attempt %d failed:\n%s", attempt, output)
        if attempt < retries:
            await asyncio.sleep(delay)
    raise RuntimeError("DB migration failed after %d attempts" % retries)


async def main() -> None:
    await run_migrations()

    engine = create_engine()
    session_factory = async_session_factory()

    bot = Bot(
        token=settings.bot_token,
        default=DefaultBotProperties(parse_mode=ParseMode.HTML),
    )
    dp = Dispatcher(storage=MemoryStorage())

    # Middlewares
    dp.update.middleware(DbSessionMiddleware(session_factory))
    dp.update.middleware(RegisterUserMiddleware())

    # Routers
    dp.include_router(main_router)

    # Payment reminders scheduler — sends notifications at 08:00 for due reminders
    scheduler = setup_scheduler(bot, session_factory)
    scheduler.start()

    logger.info("Bot started.")
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    finally:
        scheduler.shutdown(wait=False)
        await engine.dispose()
        await bot.session.close()
        logger.info("Bot stopped.")


if __name__ == "__main__":
    asyncio.run(main())
