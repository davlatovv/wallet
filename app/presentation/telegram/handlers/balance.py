from aiogram import Router, F
from aiogram.types import Message

from app.infrastructure.container import Container

router = Router(name="balance")


@router.message(F.text == "💰 Баланс")
async def handle_balance(message: Message, container: Container) -> None:
    result = await container.get_balance.execute(message.from_user.id)
    sign = "+" if result.balance >= 0 else ""
    await message.answer(
        "💰 <b>Текущий баланс</b>\n\n"
        f"📥 Доходы:   <b>{result.total_income:,.2f}</b>\n"
        f"📤 Расходы:  <b>{result.total_expense:,.2f}</b>\n"
        f"{'─' * 24}\n"
        f"💼 Баланс:   <b>{sign}{result.balance:,.2f}</b>",
        parse_mode="HTML",
    )
