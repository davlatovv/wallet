from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class InstallmentStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"
    CANCELLED = "cancelled"


@dataclass
class InstallmentEntity:
    id: int
    user_id: int
    name: str
    total_amount: Decimal
    monthly_payment: Decimal
    months_total: int
    months_paid: int
    next_payment_date: date | None
    description: str | None
    status: InstallmentStatus
    created_at: datetime

    @property
    def months_remaining(self) -> int:
        return max(self.months_total - self.months_paid, 0)

    @property
    def amount_paid(self) -> Decimal:
        return self.monthly_payment * self.months_paid

    @property
    def amount_remaining(self) -> Decimal:
        return max(self.total_amount - self.amount_paid, Decimal("0"))

    @property
    def is_completed(self) -> bool:
        return self.months_paid >= self.months_total
