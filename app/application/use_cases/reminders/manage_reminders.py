import logging
from dataclasses import dataclass
from datetime import date
from decimal import Decimal

from app.application.dto.reminder import (
    MAX_MONTHS,
    CreateCreditReminderDTO,
    CreateInstallmentReminderDTO,
    CreateEducationReminderDTO,
    CreateRegularReminderDTO,
    ReminderDetailDTO,
)
from app.domain.entities.reminder import ReminderEntity, ReminderType, PaymentType
from app.domain.entities.reminder import ReminderStatus
from app.domain.exceptions.base import BusinessRuleViolation, NotFoundError, ValidationError
from app.domain.repositories.abstract_reminder import AbstractReminderRepository
from app.domain.value_objects.credit_calculator import CreditCalculator

logger = logging.getLogger(__name__)


def _clean_name(name: str) -> str:
    name = name.strip()
    if not 1 <= len(name) <= 128:
        raise ValidationError("Name must be 1-128 characters")
    return name


def _credit_payment_for_month(entity: ReminderEntity, month_number: int) -> Decimal | None:
    """Scheduled payment for a 1-based month of a credit, or None if out of range."""
    if not (entity.reminder_type == ReminderType.CREDIT and entity.total_amount and entity.months_total):
        return None
    if not 1 <= month_number <= entity.months_total:
        return None
    schedule = CreditCalculator.full_schedule(
        principal=entity.total_amount,
        annual_rate=entity.interest_rate or Decimal("0"),
        months=entity.months_total,
        payment_type=entity.payment_type.value if entity.payment_type else "annuity",
    )
    return schedule[month_number - 1]["payment"]


def _to_detail_dto(entity: ReminderEntity, with_schedule: bool = False) -> ReminderDetailDTO:
    schedule = None
    if with_schedule and entity.reminder_type == ReminderType.CREDIT and entity.total_amount and entity.months_total:
        schedule = CreditCalculator.full_schedule(
            principal=entity.total_amount,
            annual_rate=entity.interest_rate or Decimal("0"),
            months=entity.months_total,
            payment_type=entity.payment_type.value if entity.payment_type else "annuity",
        )
    return ReminderDetailDTO(
        id=entity.id,
        name=entity.name,
        reminder_type=entity.reminder_type,
        total_amount=entity.total_amount,
        paid_amount=entity.paid_amount,
        remaining_amount=entity.remaining_amount,
        progress_percent=entity.progress_percent,
        payment_amount=entity.payment_amount,
        months_paid=entity.months_paid,
        months_total=entity.months_total,
        next_payment_date=entity.next_payment_date,
        interest_rate=entity.interest_rate,
        payment_type=entity.payment_type,
        payment_schedule=schedule,
        status=entity.status,
    )


class CreateCreditReminderUseCase:
    def __init__(self, repo: AbstractReminderRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: int, dto: CreateCreditReminderDTO) -> ReminderDetailDTO:
        pmt = CreditCalculator.annuity_payment(dto.total_amount, dto.interest_rate, dto.months_total) \
            if dto.payment_type == PaymentType.ANNUITY \
            else CreditCalculator.differential_payment(dto.total_amount, dto.interest_rate, dto.months_total, 1)

        entity = await self._repo.create(
            user_id=user_id,
            reminder_type=ReminderType.CREDIT,
            name=_clean_name(dto.name),
            payment_amount=pmt,
            payment_day=dto.payment_day,
            next_payment_date=dto.first_payment_date,
            total_amount=dto.total_amount,
            months_total=dto.months_total,
            interest_rate=dto.interest_rate,
            payment_type=dto.payment_type,
        )
        logger.info("Credit reminder created: user=%d id=%d", user_id, entity.id)
        return _to_detail_dto(entity)


class CreateInstallmentReminderUseCase:
    def __init__(self, repo: AbstractReminderRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: int, dto: CreateInstallmentReminderDTO) -> ReminderDetailDTO:
        entity = await self._repo.create(
            user_id=user_id,
            reminder_type=ReminderType.INSTALLMENT,
            name=_clean_name(dto.name),
            payment_amount=dto.monthly_payment,
            payment_day=dto.payment_day,
            next_payment_date=dto.first_payment_date,
            total_amount=dto.total_amount,
            months_total=dto.months_total,
            interest_rate=None,
            payment_type=None,
        )
        logger.info("Installment reminder created: user=%d id=%d", user_id, entity.id)
        return _to_detail_dto(entity)


class CreateEducationReminderUseCase:
    def __init__(self, repo: AbstractReminderRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: int, dto: CreateEducationReminderDTO) -> ReminderDetailDTO:
        entity = await self._repo.create(
            user_id=user_id,
            reminder_type=ReminderType.EDUCATION,
            name=_clean_name(dto.name),
            payment_amount=dto.payment_amount,
            payment_day=dto.payment_day,
            next_payment_date=dto.first_payment_date,
            total_amount=dto.total_amount,
            months_total=None,
            interest_rate=None,
            payment_type=None,
        )
        logger.info("Education reminder created: user=%d id=%d", user_id, entity.id)
        return _to_detail_dto(entity)


class CreateRegularReminderUseCase:
    def __init__(self, repo: AbstractReminderRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: int, dto: CreateRegularReminderDTO) -> ReminderDetailDTO:
        entity = await self._repo.create(
            user_id=user_id,
            reminder_type=ReminderType.REGULAR,
            name=_clean_name(dto.name),
            payment_amount=dto.payment_amount,
            payment_day=dto.payment_day,
            next_payment_date=dto.first_payment_date,
            total_amount=None,
            months_total=None,
            interest_rate=None,
            payment_type=None,
        )
        logger.info("Regular reminder created: user=%d id=%d", user_id, entity.id)
        return _to_detail_dto(entity)


class ListRemindersUseCase:
    def __init__(self, repo: AbstractReminderRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: int) -> list[ReminderDetailDTO]:
        entities = await self._repo.list_by_user(user_id)
        return [_to_detail_dto(e) for e in entities]


class GetReminderDetailUseCase:
    def __init__(self, repo: AbstractReminderRepository) -> None:
        self._repo = repo

    async def execute(self, reminder_id: int, user_id: int) -> ReminderDetailDTO:
        entity = await self._repo.get_by_id(reminder_id, user_id)
        if not entity:
            raise NotFoundError(f"Reminder {reminder_id} not found")
        return _to_detail_dto(entity, with_schedule=True)


class RecordPaymentUseCase:
    def __init__(self, repo: AbstractReminderRepository) -> None:
        self._repo = repo

    async def execute(self, reminder_id: int, user_id: int, amount: Decimal | None = None) -> ReminderDetailDTO:
        entity = await self._repo.get_by_id(reminder_id, user_id)
        if not entity:
            raise NotFoundError(f"Reminder {reminder_id} not found")
        if entity.status != ReminderStatus.ACTIVE:
            raise BusinessRuleViolation("Reminder is already completed")
        if amount is not None and amount <= Decimal("0"):
            raise ValidationError("Payment amount must be positive")

        # Credits: the amount due changes month to month (differential, final annuity
        # payment), so default to the schedule rather than the stored first payment.
        month = entity.months_paid + 1
        scheduled = _credit_payment_for_month(entity, month)
        payment = amount if amount is not None else (scheduled or entity.payment_amount)
        next_amount = _credit_payment_for_month(entity, month + 1)

        updated = await self._repo.record_payment(reminder_id, user_id, payment, next_amount)
        if not updated:  # completed concurrently
            raise BusinessRuleViolation("Reminder is already completed")
        logger.info("Payment recorded: user=%d reminder=%d amount=%s", user_id, reminder_id, payment)
        return _to_detail_dto(updated)


@dataclass
class CreditPreview:
    first_payment: Decimal
    total_payment: Decimal
    overpayment: Decimal
    schedule: list[dict]


class PreviewCreditUseCase:
    """Computes a credit's schedule without saving anything."""

    def execute(
        self, total_amount: Decimal, interest_rate: Decimal, months_total: int, payment_type: PaymentType
    ) -> CreditPreview:
        if total_amount <= Decimal("0"):
            raise ValidationError("total_amount must be positive")
        if not Decimal("0") <= interest_rate <= Decimal("100"):
            raise ValidationError("interest_rate must be 0-100")
        if not 1 <= months_total <= MAX_MONTHS:
            raise ValidationError(f"months_total must be 1-{MAX_MONTHS}")
        schedule = CreditCalculator.full_schedule(
            total_amount, interest_rate, months_total, payment_type.value
        )
        total = sum((row["payment"] for row in schedule), Decimal("0"))
        return CreditPreview(
            first_payment=schedule[0]["payment"],
            total_payment=total,
            overpayment=total - total_amount,
            schedule=schedule,
        )


class DeleteReminderUseCase:
    def __init__(self, repo: AbstractReminderRepository) -> None:
        self._repo = repo

    async def execute(self, reminder_id: int, user_id: int) -> None:
        deleted = await self._repo.delete(reminder_id, user_id)
        if not deleted:
            raise NotFoundError(f"Reminder {reminder_id} not found")
        logger.info("Reminder deleted: user=%d id=%d", user_id, reminder_id)


class ListDueTodayUseCase:
    def __init__(self, repo: AbstractReminderRepository) -> None:
        self._repo = repo

    async def execute(self, today: date) -> list[ReminderEntity]:
        return await self._repo.list_due_today(today)
