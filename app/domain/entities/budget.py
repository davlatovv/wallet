from dataclasses import dataclass
from datetime import date, datetime, timedelta
from decimal import Decimal
from enum import Enum


class BudgetPeriod(str, Enum):
    DAILY = "daily"
    WEEKLY = "weekly"
    MONTHLY = "monthly"


@dataclass
class BudgetEntity:
    id: int
    user_id: int
    category_id: int | None
    limit_amount: Decimal
    period: BudgetPeriod
    start_date: date
    category_name: str | None = None

    def usage_ratio(self, spent: Decimal) -> Decimal:
        if self.limit_amount == Decimal("0"):
            return Decimal("0")
        return spent / self.limit_amount

    def is_warn_threshold_reached(self, spent: Decimal, threshold: Decimal) -> bool:
        return self.usage_ratio(spent) >= threshold


_PERIOD_DAYS = {BudgetPeriod.DAILY: 1, BudgetPeriod.WEEKLY: 7, BudgetPeriod.MONTHLY: 30}


def budget_window_start(period: BudgetPeriod, now: datetime) -> datetime:
    """Budgets are measured over a rolling window ending now (1 / 7 / 30 days)."""
    return now - timedelta(days=_PERIOD_DAYS[period])
