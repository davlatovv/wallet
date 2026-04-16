from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class ReminderType(str, Enum):
    CREDIT = "credit"
    INSTALLMENT = "installment"
    EDUCATION = "education"
    REGULAR = "regular"


class PaymentType(str, Enum):
    ANNUITY = "annuity"
    DIFFERENTIAL = "differential"


class ReminderStatus(str, Enum):
    ACTIVE = "active"
    COMPLETED = "completed"


@dataclass
class ReminderEntity:
    id: int
    user_id: int
    reminder_type: ReminderType
    name: str
    payment_amount: Decimal
    payment_day: int  # день месяца 1–31
    next_payment_date: date
    total_amount: Decimal | None
    paid_amount: Decimal
    months_total: int | None  # для CREDIT и INSTALLMENT
    months_paid: int
    interest_rate: Decimal | None  # для CREDIT, годовой %
    payment_type: PaymentType | None  # для CREDIT
    status: ReminderStatus
    reminder_enabled: bool
    created_at: datetime

    @property
    def remaining_amount(self) -> Decimal | None:
        if self.total_amount is None:
            return None
        return max(self.total_amount - self.paid_amount, Decimal("0"))

    @property
    def progress_percent(self) -> int | None:
        if self.total_amount is None or self.total_amount == 0:
            return None
        pct = (self.paid_amount / self.total_amount) * 100
        return min(int(pct), 100)

    @property
    def is_completed(self) -> bool:
        if self.months_total is not None:
            return self.months_paid >= self.months_total
        if self.total_amount is not None:
            return self.paid_amount >= self.total_amount
        return self.status == ReminderStatus.COMPLETED
