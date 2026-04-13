import logging
from datetime import date
from decimal import Decimal

from app.domain.entities.installment import InstallmentEntity
from app.domain.exceptions.base import NotFoundError, ValidationError
from app.domain.repositories.abstract_installment import AbstractInstallmentRepository

logger = logging.getLogger(__name__)


class AddInstallmentUseCase:
    def __init__(self, repo: AbstractInstallmentRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        user_id: int,
        name: str,
        total_amount: Decimal,
        monthly_payment: Decimal,
        months_total: int,
        next_payment_date: date | None = None,
        description: str | None = None,
    ) -> InstallmentEntity:
        if total_amount <= Decimal("0") or monthly_payment <= Decimal("0"):
            raise ValidationError("Amounts must be positive")
        if months_total < 1:
            raise ValidationError("months_total must be >= 1")
        inst = await self._repo.create(
            user_id, name, total_amount, monthly_payment, months_total, next_payment_date, description
        )
        logger.info("Installment created: user=%d id=%d", user_id, inst.id)
        return inst


class PayInstallmentMonthUseCase:
    def __init__(self, repo: AbstractInstallmentRepository) -> None:
        self._repo = repo

    async def execute(self, installment_id: int, user_id: int) -> InstallmentEntity:
        inst = await self._repo.pay_month(installment_id, user_id)
        if not inst:
            raise NotFoundError(f"Installment {installment_id} not found or already completed")
        logger.info("Installment month paid: user=%d id=%d paid=%d", user_id, installment_id, inst.months_paid)
        return inst


class ListInstallmentsUseCase:
    def __init__(self, repo: AbstractInstallmentRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: int) -> list[InstallmentEntity]:
        return await self._repo.list_by_user(user_id)
