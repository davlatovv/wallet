import logging
from dataclasses import dataclass
from datetime import date, datetime, timezone
from decimal import Decimal

from app.config.settings import settings
from app.domain.entities.budget import BudgetEntity, BudgetPeriod, budget_window_start
from app.domain.entities.transaction import TransactionType
from app.domain.exceptions.base import NotFoundError, ValidationError
from app.domain.repositories.abstract_budget import AbstractBudgetRepository
from app.domain.repositories.abstract_category import AbstractCategoryRepository
from app.domain.repositories.abstract_transaction import AbstractTransactionRepository

logger = logging.getLogger(__name__)


class SetBudgetUseCase:
    """Upsert: there is at most one budget per (category, period)."""

    def __init__(
        self, repo: AbstractBudgetRepository, category_repo: AbstractCategoryRepository
    ) -> None:
        self._repo = repo
        self._cat_repo = category_repo

    async def execute(
        self,
        user_id: int,
        limit_amount: Decimal,
        period: BudgetPeriod,
        category_id: int | None = None,
        start_date: date | None = None,
    ) -> BudgetEntity:
        if limit_amount <= Decimal("0"):
            raise ValidationError("Budget limit must be positive")
        if category_id is not None and await self._cat_repo.get_by_id(category_id, user_id) is None:
            raise NotFoundError(f"Category {category_id} not found")

        existing = next(
            (b for b in await self._repo.list_by_user(user_id)
             if b.category_id == category_id and b.period == period),
            None,
        )
        if existing:
            budget = await self._repo.update_limit(existing.id, user_id, limit_amount)
            logger.info("Budget updated: user=%d id=%d limit=%s", user_id, existing.id, limit_amount)
            return budget
        budget = await self._repo.create(
            user_id, category_id, limit_amount, period, start_date or date.today()
        )
        logger.info("Budget set: user=%d id=%d limit=%s", user_id, budget.id, limit_amount)
        return budget


class ListBudgetsUseCase:
    def __init__(self, repo: AbstractBudgetRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: int) -> list[BudgetEntity]:
        return await self._repo.list_by_user(user_id)


@dataclass
class BudgetProgress:
    budget: BudgetEntity
    spent: Decimal
    ratio: Decimal

    @property
    def is_warning(self) -> bool:
        return self.ratio >= settings.budget_warn_threshold

    @property
    def is_critical(self) -> bool:
        return self.ratio >= settings.budget_critical_threshold


class GetBudgetProgressUseCase:
    def __init__(
        self,
        repo: AbstractBudgetRepository,
        transaction_repo: AbstractTransactionRepository,
    ) -> None:
        self._repo = repo
        self._tx_repo = transaction_repo

    async def execute(self, user_id: int) -> list[BudgetProgress]:
        now = datetime.now(timezone.utc)
        result = []
        for budget in await self._repo.list_by_user(user_id):
            spent = await self._tx_repo.sum_by_period(
                user_id, budget_window_start(budget.period, now), now,
                TransactionType.EXPENSE, category_id=budget.category_id,
            )
            result.append(BudgetProgress(budget, spent, budget.usage_ratio(spent)))
        return result


class DeleteBudgetUseCase:
    def __init__(self, repo: AbstractBudgetRepository) -> None:
        self._repo = repo

    async def execute(self, budget_id: int, user_id: int) -> None:
        deleted = await self._repo.delete(budget_id, user_id)
        if not deleted:
            raise NotFoundError(f"Budget {budget_id} not found")
