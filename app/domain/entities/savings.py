from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class SavingsStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class SavingsGoalEntity:
    id: int
    user_id: int
    name: str
    target_amount: Decimal
    current_amount: Decimal
    description: str | None
    deadline: date | None
    status: SavingsStatus
    created_at: datetime

    @property
    def remaining(self) -> Decimal:
        return max(self.target_amount - self.current_amount, Decimal("0"))

    @property
    def progress_percent(self) -> int:
        if self.target_amount == Decimal("0"):
            return 0
        ratio = self.current_amount / self.target_amount
        return min(int(ratio * 100), 100)

    @property
    def is_completed(self) -> bool:
        return self.current_amount >= self.target_amount
