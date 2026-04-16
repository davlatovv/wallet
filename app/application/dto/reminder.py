from datetime import date
from decimal import Decimal

from pydantic import BaseModel, field_validator

from app.domain.entities.reminder import ReminderType, PaymentType, ReminderStatus


class CreateCreditReminderDTO(BaseModel):
    name: str
    total_amount: Decimal
    interest_rate: Decimal      # годовой %
    months_total: int
    payment_type: PaymentType   # ANNUITY / DIFFERENTIAL
    payment_day: int            # день месяца
    first_payment_date: date

    @field_validator("total_amount", "interest_rate")
    @classmethod
    def must_be_positive(cls, v: Decimal) -> Decimal:
        if v < Decimal("0"):
            raise ValueError("Must be >= 0")
        return v

    @field_validator("months_total")
    @classmethod
    def months_must_be_valid(cls, v: int) -> int:
        if v < 1:
            raise ValueError("months_total must be >= 1")
        return v

    @field_validator("payment_day")
    @classmethod
    def day_must_be_valid(cls, v: int) -> int:
        if not 1 <= v <= 31:
            raise ValueError("payment_day must be 1–31")
        return v


class CreateInstallmentReminderDTO(BaseModel):
    name: str
    total_amount: Decimal
    monthly_payment: Decimal
    months_total: int
    payment_day: int
    first_payment_date: date

    @field_validator("total_amount", "monthly_payment")
    @classmethod
    def must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("Must be > 0")
        return v


class CreateEducationReminderDTO(BaseModel):
    name: str
    total_amount: Decimal
    payment_amount: Decimal
    payment_day: int
    first_payment_date: date

    @field_validator("total_amount", "payment_amount")
    @classmethod
    def must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("Must be > 0")
        return v


class CreateRegularReminderDTO(BaseModel):
    name: str
    payment_amount: Decimal
    payment_day: int
    first_payment_date: date

    @field_validator("payment_amount")
    @classmethod
    def must_be_positive(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("Must be > 0")
        return v


class ReminderDetailDTO(BaseModel):
    id: int
    name: str
    reminder_type: ReminderType
    total_amount: Decimal | None
    paid_amount: Decimal
    remaining_amount: Decimal | None
    progress_percent: int | None
    payment_amount: Decimal
    months_paid: int
    months_total: int | None
    next_payment_date: date
    interest_rate: Decimal | None
    payment_type: PaymentType | None
    payment_schedule: list[dict] | None
    status: ReminderStatus

    model_config = {"arbitrary_types_allowed": True}
