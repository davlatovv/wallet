from dataclasses import dataclass
from datetime import date
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
