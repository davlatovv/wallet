import logging
from datetime import date
from decimal import Decimal

from app.domain.entities.savings import SavingsGoalEntity, SavingsStatus
from app.domain.entities.transaction import AccountType, TransactionType
from app.domain.exceptions.base import BusinessRuleViolation, NotFoundError, ValidationError
from app.domain.repositories.abstract_savings import AbstractSavingsRepository
from app.domain.repositories.abstract_transaction import AbstractTransactionRepository
from app.domain.repositories.abstract_user import AbstractUserRepository

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
        name = name.strip()
        if not 1 <= len(name) <= 128:
            raise ValidationError("Goal name must be 1-128 characters")
        goal = await self._repo.create(
            user_id, name, target_amount, (description or "").strip() or None, deadline
        )
        logger.info("Savings goal created: user=%d id=%d", user_id, goal.id)
        return goal


class AddToSavingsUseCase:
    def __init__(
        self,
        repo: AbstractSavingsRepository,
        transaction_repo: AbstractTransactionRepository,
        user_repo: AbstractUserRepository,
    ) -> None:
        self._repo = repo
        self._tx_repo = transaction_repo
        self._user_repo = user_repo

    async def execute(self, goal_id: int, user_id: int, amount: Decimal) -> SavingsGoalEntity:
        if amount <= Decimal("0"):
            raise ValidationError("Amount must be positive")
        current = await self._repo.get_by_id(goal_id, user_id)
        if not current:
            raise NotFoundError(f"Savings goal {goal_id} not found")
        if current.status != SavingsStatus.ACTIVE:
            raise BusinessRuleViolation(f"Savings goal is {current.status.value}; deposits are closed")
        goal = await self._repo.add_funds(goal_id, user_id, amount)
        # Record as SAVINGS transaction so it appears in balance and analytics
        await self._tx_repo.create(
            user_id=user_id,
            amount=amount,
            transaction_type=TransactionType.SAVINGS,
            category_id=None,
            note=f"Копилка: {goal.name}",
            account_type=AccountType.CARD,
        )
        await self._user_repo.apply_balance_delta(user_id, AccountType.CARD, -amount)
        logger.info("Savings funded: user=%d goal=%d amount=%s", user_id, goal_id, amount)
        return goal


class ListSavingsUseCase:
    def __init__(self, repo: AbstractSavingsRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: int, active_only: bool = False) -> list[SavingsGoalEntity]:
        status = SavingsStatus.ACTIVE if active_only else None
        return await self._repo.list_by_user(user_id, status)
