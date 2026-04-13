import logging
from datetime import date
from decimal import Decimal

from app.domain.entities.budget import BudgetEntity, BudgetPeriod
from app.domain.exceptions.base import NotFoundError
from app.domain.repositories.abstract_budget import AbstractBudgetRepository

logger = logging.getLogger(__name__)


class SetBudgetUseCase:
    def __init__(self, repo: AbstractBudgetRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        user_id: int,
        limit_amount: Decimal,
        period: BudgetPeriod,
        category_id: int | None = None,
        start_date: date | None = None,
    ) -> BudgetEntity:
        if start_date is None:
            start_date = date.today()
        budget = await self._repo.create(user_id, category_id, limit_amount, period, start_date)
        logger.info("Budget set: user=%d id=%d limit=%s", user_id, budget.id, limit_amount)
        return budget


class ListBudgetsUseCase:
    def __init__(self, repo: AbstractBudgetRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: int) -> list[BudgetEntity]:
        return await self._repo.list_by_user(user_id)


class DeleteBudgetUseCase:
    def __init__(self, repo: AbstractBudgetRepository) -> None:
        self._repo = repo

    async def execute(self, budget_id: int, user_id: int) -> None:
        deleted = await self._repo.delete(budget_id, user_id)
        if not deleted:
            raise NotFoundError(f"Budget {budget_id} not found")
