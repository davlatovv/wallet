from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from app.domain.entities.transaction import TransactionType
from app.domain.repositories.abstract_transaction import AbstractTransactionRepository


@dataclass
class BalanceResult:
    total_income: Decimal
    total_expense: Decimal
    total_savings: Decimal

    @property
    def balance(self) -> Decimal:
        return self.total_income - self.total_expense - self.total_savings


class GetBalanceUseCase:
    def __init__(self, transaction_repo: AbstractTransactionRepository) -> None:
        self._tx_repo = transaction_repo

    async def execute(self, user_id: int) -> BalanceResult:
        far_past = datetime(2000, 1, 1, tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        income = await self._tx_repo.sum_by_period(user_id, far_past, now, TransactionType.INCOME)
        expense = await self._tx_repo.sum_by_period(user_id, far_past, now, TransactionType.EXPENSE)
        savings = await self._tx_repo.sum_by_period(user_id, far_past, now, TransactionType.SAVINGS)
        return BalanceResult(total_income=income, total_expense=expense, total_savings=savings)
