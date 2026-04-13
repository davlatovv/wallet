from aiogram import Router, F
from aiogram.types import Message, BufferedInputFile, InlineKeyboardMarkup, InlineKeyboardButton, CallbackQuery

from app.infrastructure.container import Container
from app.infrastructure.export.csv_exporter import CSVExporter
from app.infrastructure.export.excel_exporter import ExcelExporter

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
    data = await CSVExporter(container._tx_repo).export_month(callback.from_user.id)
    await callback.message.answer_document(
        BufferedInputFile(data, filename="transactions.csv"),
        caption="📄 Транзакции за текущий месяц (CSV)",
    )


@router.callback_query(F.data == "export:xlsx")
async def export_xlsx(callback: CallbackQuery, container: Container) -> None:
    await callback.answer("Генерирую Excel...")
    data = await ExcelExporter(container._tx_repo).export_month(callback.from_user.id)
    await callback.message.answer_document(
        BufferedInputFile(data, filename="transactions.xlsx"),
        caption="📊 Транзакции за текущий месяц (Excel)",
    )
