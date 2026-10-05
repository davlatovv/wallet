from dataclasses import dataclass, field
from datetime import datetime, timedelta, timezone
from zoneinfo import ZoneInfo
from decimal import Decimal
from enum import Enum

from app.domain.entities.transaction import TransactionType
from app.domain.repositories.abstract_transaction import AbstractTransactionRepository


class ReportPeriod(str, Enum):
    DAY = "day"
    WEEK = "week"
    MONTH = "month"
    YEAR = "year"


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
    total_savings: Decimal
    expense_by_category: list[CategoryBreakdown] = field(default_factory=list)
    income_by_category: list[CategoryBreakdown] = field(default_factory=list)

    @property
    def balance(self) -> Decimal:
        return self.total_income - self.total_expense - self.total_savings


def _period_range(period: ReportPeriod, tz_name: str = "UTC") -> tuple[datetime, datetime]:
    """"Today"/"this week"/"this month"/"this year" are boundaries in the user's own
    timezone, converted back to UTC-aware datetimes for querying (transactions are
    stored in UTC, and aware-to-aware comparison is timezone-independent)."""
    try:
        tz = ZoneInfo(tz_name)
    except Exception:  # unknown/invalid tz stored somehow: fail safe to UTC
        tz = timezone.utc
    now = datetime.now(tz)
    if period == ReportPeriod.DAY:
        from_dt = now.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == ReportPeriod.WEEK:
        from_dt = now - timedelta(days=now.weekday())
        from_dt = from_dt.replace(hour=0, minute=0, second=0, microsecond=0)
    elif period == ReportPeriod.YEAR:
        from_dt = now.replace(month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    else:  # month
        from_dt = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    return from_dt.astimezone(timezone.utc), now.astimezone(timezone.utc)


class GetReportUseCase:
    def __init__(self, transaction_repo: AbstractTransactionRepository) -> None:
        self._tx_repo = transaction_repo

    async def execute(
        self, user_id: int, period: ReportPeriod, timezone: str = "UTC"
    ) -> ReportResult:
        from_dt, to_dt = _period_range(period, timezone)

        income = await self._tx_repo.sum_by_period(user_id, from_dt, to_dt, TransactionType.INCOME)
        expense = await self._tx_repo.sum_by_period(user_id, from_dt, to_dt, TransactionType.EXPENSE)
        savings = await self._tx_repo.sum_by_period(user_id, from_dt, to_dt, TransactionType.SAVINGS)

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
            total_savings=savings,
            expense_by_category=to_breakdown(expense_cats, expense),
            income_by_category=to_breakdown(income_cats, income),
        )


class ListReportMonthsUseCase:
    def __init__(self, transaction_repo: AbstractTransactionRepository) -> None:
        self._tx_repo = transaction_repo

    async def execute(self, user_id: int) -> list[tuple[int, int]]:
        """(year, month) pairs that have transactions, newest first."""
        return await self._tx_repo.list_available_months(user_id)
