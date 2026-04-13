import csv
import io
from datetime import datetime, timezone, timedelta

from app.domain.entities.transaction import TransactionType
from app.domain.repositories.abstract_transaction import AbstractTransactionRepository


class CSVExporter:
    def __init__(self, tx_repo: AbstractTransactionRepository) -> None:
        self._tx_repo = tx_repo

    async def export_month(self, user_id: int) -> bytes:
        now = datetime.now(timezone.utc)
        from_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        transactions = await self._tx_repo.list_by_period(user_id, from_dt, now)

        output = io.StringIO()
        writer = csv.writer(output)
        writer.writerow(["Дата", "Тип", "Сумма", "Категория", "Заметка"])
        for tx in transactions:
            writer.writerow([
                tx.created_at.strftime("%Y-%m-%d %H:%M"),
                "Доход" if tx.transaction_type == TransactionType.INCOME else "Расход",
                tx.amount,
                tx.category_name or "",
                tx.note or "",
            ])
        return output.getvalue().encode("utf-8-sig")
