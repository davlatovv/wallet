from datetime import date
from decimal import Decimal
from typing import Annotated

from pydantic import BaseModel, Field

from app.application.dto.reminder import MAX_MONTHS, ReminderDetailDTO
from app.application.use_cases.reminders.manage_reminders import CreditPreview
from app.domain.entities.reminder import PaymentType, ReminderStatus, ReminderType
from app.presentation.api.schemas.common import MoneyStr, RateStr

Name = Annotated[str, Field(min_length=1, max_length=128)]
Amount = Annotated[Decimal, Field(gt=0, max_digits=15, decimal_places=2)]
Months = Annotated[int, Field(ge=1, le=MAX_MONTHS)]
Rate = Annotated[Decimal, Field(ge=0, le=100, max_digits=5, decimal_places=2)]


class _Schedule(BaseModel):
    """Payments repeat monthly on the day of `first_payment_date` (clamped to short months)."""

    first_payment_date: date


class CreateCreditRequest(_Schedule):
    name: Name
    total_amount: Amount
    interest_rate: Rate  # annual %
    months_total: Months
    payment_type: PaymentType


class CreateInstallmentRequest(_Schedule):
    name: Name
    total_amount: Amount
    monthly_payment: Amount
    months_total: Months


class CreateEducationRequest(_Schedule):
    name: Name
    total_amount: Amount
    payment_amount: Amount


class CreateRegularRequest(_Schedule):
    name: Name
    payment_amount: Amount


class CreditPreviewRequest(BaseModel):
    total_amount: Amount
    interest_rate: Rate
    months_total: Months
    payment_type: PaymentType


class RecordPaymentRequest(BaseModel):
    """Omit `amount` to record the scheduled payment."""

    amount: Amount | None = None


class ScheduleRowResponse(BaseModel):
    month: int
    payment: MoneyStr
    principal_part: MoneyStr
    interest_part: MoneyStr
    balance: MoneyStr


class CreditPreviewResponse(BaseModel):
    first_payment: MoneyStr
    total_payment: MoneyStr
    overpayment: MoneyStr
    schedule: list[ScheduleRowResponse]

    @classmethod
    def from_preview(cls, p: CreditPreview) -> "CreditPreviewResponse":
        return cls(first_payment=p.first_payment, total_payment=p.total_payment,
                   overpayment=p.overpayment,
                   schedule=[ScheduleRowResponse(**row) for row in p.schedule])


class ReminderResponse(BaseModel):
    id: int
    name: str
    reminder_type: ReminderType
    status: ReminderStatus
    payment_amount: MoneyStr  # amount due on next_payment_date
    next_payment_date: date
    total_amount: MoneyStr | None
    paid_amount: MoneyStr
    remaining_amount: MoneyStr | None
    progress_percent: int | None
    months_paid: int
    months_total: int | None
    interest_rate: RateStr | None
    payment_type: PaymentType | None
    payment_schedule: list[ScheduleRowResponse] | None  # only on the detail endpoint

    @classmethod
    def from_dto(cls, d: ReminderDetailDTO) -> "ReminderResponse":
        data = d.model_dump(exclude={"payment_schedule"})
        schedule = [ScheduleRowResponse(**r) for r in d.payment_schedule] if d.payment_schedule else None
        return cls(**data, payment_schedule=schedule)
