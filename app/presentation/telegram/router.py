from aiogram import Router

from app.presentation.telegram.handlers import (
    start,
    expense,
    income,
    analytics,
    categories,
    budgets,
    debts,
    savings,
    export,
    reminders,
)

main_router = Router(name="main")

main_router.include_router(start.router)
main_router.include_router(expense.router)
main_router.include_router(income.router)
main_router.include_router(analytics.router)
main_router.include_router(categories.router)
main_router.include_router(budgets.router)
main_router.include_router(debts.router)
main_router.include_router(savings.router)
main_router.include_router(export.router)
main_router.include_router(reminders.router)
