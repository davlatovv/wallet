from dataclasses import dataclass, field
from datetime import datetime, timezone, timedelta
from decimal import Decimal
from enum import Enum

from app.domain.entities.transaction import TransactionType
from app.domain.repositories.abstract_transaction import AbstractTransactionRepository


class ReportPeriod(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"


@dataclass
class CategoryBreakdown:
    category_id: int
    category_name: str
    amount: Decimal
    percent: float


@dataclass
class ReportResult:
    period: ReportPeriod
    from_dt: datetime
    to_dt: datetime
    total_income: Decimal
    total_expense: Decimal
    expense_by_category: list[CategoryBreakdown] = field(default_factory=list)
    income_by_category: list[CategoryBreakdown] = field(default_factory=list)

    @property
    def balance(self) -> Decimal:
        return self.total_income - self.total_expense


def _period_range(period: ReportPeriod) -> tuple[datetime, datetime]:
    now = datetime.now(timezone.utc)
    if period == ReportPeriod.DAY:
        from_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == ReportPeriod.WEEK:
        from_dt = now - timedelta(days=now.weekday())
        from_dt = from_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    else:  # month
        from_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return from_dt, now


class GetReportUseCase:
    def __init__(self, transaction_repo: AbstractTransactionRepository) -> None:
        self._tx_repo = transaction_repo

    async def execute(self, user_id: int, period: ReportPeriod) -> ReportResult:
        from_dt, to_dt = _period_range(period)

        income = await self._tx_repo.sum_by_period(user_id, from_dt, to_dt, TransactionType.INCOME)
        expense = await self._tx_repo.sum_by_period(user_id, from_dt, to_dt, TransactionType.EXPENSE)

        expense_cats = await self._tx_repo.sum_by_category(user_id, from_dt, to_dt, TransactionType.EXPENSE)
        income_cats = await self._tx_repo.sum_by_category(user_id, from_dt, to_dt, TransactionType.INCOME)

        def to_breakdown(rows, total) -> list[CategoryBreakdown]:
            result = []
            for cat_id, cat_name, amount in rows:
                pct = float(amount / total * 100) if total > Decimal("0") else 0.0
                result.append(CategoryBreakdown(cat_id, cat_name, amount, round(pct, 1)))
            return result

        return ReportResult(
            period=period,
            from_dt=from_dt,
            to_dt=to_dt,
            total_income=income,
            total_expense=expense,
            expense_by_category=to_breakdown(expense_cats, expense),
            income_by_category=to_breakdown(income_cats, income),
        )
