import logging
from datetime import date
from decimal import Decimal

from app.application.dto.reminder import (
    CreateCreditReminderDTO,
    CreateInstallmentReminderDTO,
    CreateEducationReminderDTO,
    CreateRegularReminderDTO,
    ReminderDetailDTO,
)
from app.domain.entities.reminder import ReminderEntity, ReminderType, PaymentType
from app.domain.exceptions.base import NotFoundError
from app.domain.repositories.abstract_reminder import AbstractReminderRepository
from app.domain.value_objects.credit_calculator import CreditCalculator

logger = logging.getLogger(__name__)


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
            name=dto.name,
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
            name=dto.name,
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
            name=dto.name,
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
            name=dto.name,
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
        payment = amount if amount is not None else entity.payment_amount
        updated = await self._repo.record_payment(reminder_id, user_id, payment)
        if not updated:
            raise NotFoundError(f"Reminder {reminder_id} could not be updated")
        logger.info("Payment recorded: user=%d reminder=%d amount=%s", user_id, reminder_id, payment)
        return _to_detail_dto(updated)


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
