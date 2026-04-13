import io
from datetime import datetime, timezone
from openpyxl import Workbook
from openpyxl.styles import Font, PatternFill, Alignment

from app.domain.entities.transaction import TransactionType
from app.domain.repositories.abstract_transaction import AbstractTransactionRepository


class ExcelExporter:
    def __init__(self, tx_repo: AbstractTransactionRepository) -> None:
        self._tx_repo = tx_repo

    async def export_month(self, user_id: int) -> bytes:
        now = datetime.now(timezone.utc)
        from_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        transactions = await self._tx_repo.list_by_period(user_id, from_dt, now)

        wb = Workbook()
        ws = wb.active
        ws.title = "Транзакции"

        headers = ["Дата", "Тип", "Сумма", "Категория", "Заметка"]
        header_font = Font(bold=True, color="FFFFFF")
        header_fill = PatternFill("solid", fgColor="2E86AB")

        for col, header in enumerate(headers, 1):
            cell = ws.cell(row=1, column=col, value=header)
            cell.font = header_font
            cell.fill = header_fill
            cell.alignment = Alignment(horizontal="center")

        for row_idx, tx in enumerate(transactions, 2):
            ws.cell(row=row_idx, column=1, value=tx.created_at.strftime("%Y-%m-%d %H:%M"))
            ws.cell(row=row_idx, column=2, value="Доход" if tx.transaction_type == TransactionType.INCOME else "Расход")
            ws.cell(row=row_idx, column=3, value=float(tx.amount))
            ws.cell(row=row_idx, column=4, value=tx.category_name or "")
            ws.cell(row=row_idx, column=5, value=tx.note or "")

        for col in ws.columns:
            max_len = max(len(str(cell.value or "")) for cell in col)
            ws.column_dimensions[col[0].column_letter].width = min(max_len + 4, 40)

        buf = io.BytesIO()
        wb.save(buf)
        return buf.getvalue()
