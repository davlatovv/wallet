from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from app.domain.entities.savings import SavingsGoalEntity, SavingsStatus


class AbstractSavingsRepository(ABC):
    @abstractmethod
    async def create(
        self,
        user_id: int,
        name: str,
        target_amount: Decimal,
        description: str | None,
        deadline: date | None,
    ) -> SavingsGoalEntity:
        ...

    @abstractmethod
    async def get_by_id(self, goal_id: int, user_id: int) -> SavingsGoalEntity | None:
        ...

    @abstractmethod
    async def list_by_user(self, user_id: int, status: SavingsStatus | None = None) -> list[SavingsGoalEntity]:
        ...

    @abstractmethod
    async def add_funds(self, goal_id: int, user_id: int, amount: Decimal) -> SavingsGoalEntity | None:
        ...

    @abstractmethod
    async def mark_completed(self, goal_id: int, user_id: int) -> SavingsGoalEntity | None:
        ...

    @abstractmethod
    async def delete(self, goal_id: int, user_id: int) -> bool:
        ...
