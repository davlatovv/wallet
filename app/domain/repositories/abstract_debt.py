from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from app.domain.entities.debt import DebtEntity, DebtType, DebtStatus


class AbstractDebtRepository(ABC):
    @abstractmethod
    async def create(
        self,
        user_id: int,
        counterparty: str,
        amount: Decimal,
        debt_type: DebtType,
        description: str | None,
        due_date: date | None,
    ) -> DebtEntity:
        ...

    @abstractmethod
    async def get_by_id(self, debt_id: int, user_id: int) -> DebtEntity | None:
        ...

    @abstractmethod
    async def list_by_user(self, user_id: int, status: DebtStatus | None = None) -> list[DebtEntity]:
        ...

    @abstractmethod
    async def settle(self, debt_id: int, user_id: int) -> DebtEntity | None:
        ...

    @abstractmethod
    async def delete(self, debt_id: int, user_id: int) -> bool:
        ...
