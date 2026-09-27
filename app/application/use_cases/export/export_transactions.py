from dataclasses import dataclass
from datetime import date, datetime, timezone
from enum import Enum

from app.domain.exceptions.base import ValidationError
from app.infrastructure.export.csv_exporter import CSVExporter
from app.infrastructure.export.excel_exporter import ExcelExporter


class ExportFormat(str, Enum):
    CSV = "csv"
    XLSX = "xlsx"


_CONTENT_TYPES = {
    ExportFormat.CSV: "text/csv",
    ExportFormat.XLSX: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
}


@dataclass
class ExportResult:
    content: bytes
    content_type: str
    filename: str


class ExportTransactionsUseCase:
    """Exports one calendar month of transactions. Defaults to the current month."""

    def __init__(self, transaction_repo) -> None:
        self._csv = CSVExporter(transaction_repo)
        self._xlsx = ExcelExporter(transaction_repo)

    async def execute(
        self, user_id: int, fmt: ExportFormat, month: date | None = None
    ) -> ExportResult:
        now = datetime.now(timezone.utc)
        year, mon = (month.year, month.month) if month else (now.year, now.month)
        if not 1 <= mon <= 12 or not 2000 <= year <= 2100:
            raise ValidationError("month must be a valid year-month")

        exporter = self._xlsx if fmt == ExportFormat.XLSX else self._csv
        content = await exporter.export_by_month(user_id, year, mon)
        return ExportResult(
            content=content,
            content_type=_CONTENT_TYPES[fmt],
            filename=f"transactions_{year:04d}-{mon:02d}.{fmt.value}",
        )
