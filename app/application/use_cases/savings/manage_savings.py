import logging
from datetime import date
from decimal import Decimal

from app.domain.entities.savings import SavingsGoalEntity, SavingsStatus
from app.domain.entities.transaction import TransactionType
from app.domain.exceptions.base import NotFoundError, ValidationError
from app.domain.repositories.abstract_savings import AbstractSavingsRepository
from app.domain.repositories.abstract_transaction import AbstractTransactionRepository

logger = logging.getLogger(__name__)


class CreateSavingsGoalUseCase:
    def __init__(self, repo: AbstractSavingsRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        user_id: int,
        name: str,
        target_amount: Decimal,
        description: str | None = None,
        deadline: date | None = None,
    ) -> SavingsGoalEntity:
        if target_amount <= Decimal("0"):
            raise ValidationError("Target amount must be positive")
        goal = await self._repo.create(user_id, name, target_amount, description, deadline)
        logger.info("Savings goal created: user=%d id=%d", user_id, goal.id)
        return goal


class AddToSavingsUseCase:
    def __init__(
        self,
        repo: AbstractSavingsRepository,
        transaction_repo: AbstractTransactionRepository,
    ) -> None:
        self._repo = repo
        self._tx_repo = transaction_repo

    async def execute(self, goal_id: int, user_id: int, amount: Decimal) -> SavingsGoalEntity:
        if amount <= Decimal("0"):
            raise ValidationError("Amount must be positive")
        goal = await self._repo.add_funds(goal_id, user_id, amount)
        if not goal:
            raise NotFoundError(f"Savings goal {goal_id} not found")
        # Record as SAVINGS transaction so it appears in balance and analytics
        await self._tx_repo.create(
            user_id=user_id,
            amount=amount,
            transaction_type=TransactionType.SAVINGS,
            category_id=None,
            note=f"Копилка: {goal.name}",
        )
        logger.info("Savings funded: user=%d goal=%d amount=%s", user_id, goal_id, amount)
        return goal


class ListSavingsUseCase:
    def __init__(self, repo: AbstractSavingsRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: int, active_only: bool = False) -> list[SavingsGoalEntity]:
        status = SavingsStatus.ACTIVE if active_only else None
        return await self._repo.list_by_user(user_id, status)
