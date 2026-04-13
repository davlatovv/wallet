from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from app.domain.entities.budget import BudgetEntity, BudgetPeriod


class AbstractBudgetRepository(ABC):
    @abstractmethod
    async def create(
        self,
        user_id: int,
        category_id: int | None,
        limit_amount: Decimal,
        period: BudgetPeriod,
        start_date: date,
    ) -> BudgetEntity:
        ...

    @abstractmethod
    async def get_by_id(self, budget_id: int, user_id: int) -> BudgetEntity | None:
        ...

    @abstractmethod
    async def list_by_user(self, user_id: int) -> list[BudgetEntity]:
        ...

    @abstractmethod
    async def delete(self, budget_id: int, user_id: int) -> bool:
        ...
