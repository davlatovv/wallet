from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from app.application.use_cases.export.export_transactions import ExportFormat
from app.infrastructure.container import Container

router = Router(name="export")


@router.message(F.text == "📤 Экспорт")
async def export_menu(message: Message) -> None:
    await message.answer(
        "Выберите формат экспорта (текущий месяц):",
        reply_markup=InlineKeyboardMarkup(
            inline_keyboard=[
                [
                    InlineKeyboardButton(text="📄 CSV", callback_data="export:csv"),
                    InlineKeyboardButton(text="📊 Excel", callback_data="export:xlsx"),
                ]
            ]
        ),
    )


@router.callback_query(F.data == "export:csv")
async def export_csv(callback: CallbackQuery, container: Container) -> None:
    await callback.answer("Генерирую CSV...")
    result = await container.export_transactions.execute(callback.from_user.id, ExportFormat.CSV)
    await callback.message.answer_document(
        BufferedInputFile(result.content, filename=result.filename),
        caption="📄 Транзакции за текущий месяц (CSV)",
    )


@router.callback_query(F.data == "export:xlsx")
async def export_xlsx(callback: CallbackQuery, container: Container) -> None:
    await callback.answer("Генерирую Excel...")
    result = await container.export_transactions.execute(callback.from_user.id, ExportFormat.XLSX)
    await callback.message.answer_document(
        BufferedInputFile(result.content, filename=result.filename),
        caption="📊 Транзакции за текущий месяц (Excel)",
    )
