from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from app.domain.entities.installment import InstallmentEntity


class AbstractInstallmentRepository(ABC):
    @abstractmethod
    async def create(
        self,
        user_id: int,
        name: str,
        total_amount: Decimal,
        monthly_payment: Decimal,
        months_total: int,
        next_payment_date: date | None,
        description: str | None,
    ) -> InstallmentEntity:
        ...

    @abstractmethod
    async def get_by_id(self, installment_id: int, user_id: int) -> InstallmentEntity | None:
        ...

    @abstractmethod
    async def list_by_user(self, user_id: int) -> list[InstallmentEntity]:
        ...

    @abstractmethod
    async def pay_month(self, installment_id: int, user_id: int) -> InstallmentEntity | None:
        """Increment months_paid by 1, update next_payment_date, mark completed if done."""
        ...

    @abstractmethod
    async def delete(self, installment_id: int, user_id: int) -> bool:
        ...
