from aiogram import Router

from app.presentation.telegram.handlers import start

main_router = Router(name="main")

main_router.include_router(start.router)
