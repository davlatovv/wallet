import logging
from datetime import date
from decimal import Decimal

from app.domain.entities.debt import DebtEntity, DebtType, DebtStatus
from app.domain.exceptions.base import NotFoundError
from app.domain.repositories.abstract_debt import AbstractDebtRepository

logger = logging.getLogger(__name__)


class AddDebtUseCase:
    def __init__(self, repo: AbstractDebtRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        user_id: int,
        counterparty: str,
        amount: Decimal,
        debt_type: DebtType,
        description: str | None = None,
        due_date: date | None = None,
    ) -> DebtEntity:
        debt = await self._repo.create(user_id, counterparty, amount, debt_type, description, due_date)
        logger.info("Debt created: user=%d id=%d type=%s", user_id, debt.id, debt_type)
        return debt


class SettleDebtUseCase:
    def __init__(self, repo: AbstractDebtRepository) -> None:
        self._repo = repo

    async def execute(self, debt_id: int, user_id: int) -> DebtEntity:
        debt = await self._repo.settle(debt_id, user_id)
        if not debt:
            raise NotFoundError(f"Debt {debt_id} not found")
        logger.info("Debt settled: user=%d id=%d", user_id, debt_id)
        return debt


class ListDebtsUseCase:
    def __init__(self, repo: AbstractDebtRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: int, status: DebtStatus | None = None) -> list[DebtEntity]:
        return await self._repo.list_by_user(user_id, status)
