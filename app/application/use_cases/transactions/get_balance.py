from dataclasses import dataclass
from datetime import datetime, timezone
from decimal import Decimal

from app.domain.entities.transaction import TransactionType
from app.domain.repositories.abstract_transaction import AbstractTransactionRepository
from app.domain.repositories.abstract_user import AbstractUserRepository


@dataclass
class BalanceResult:
    total_income: Decimal
    total_expense: Decimal
    total_savings: Decimal
    cash_balance: Decimal
    card_balance: Decimal
    currency_balance: Decimal
    total_balance: Decimal

    @property
    def balance(self) -> Decimal:
        return self.total_balance


class GetBalanceUseCase:
    def __init__(
        self,
        transaction_repo: AbstractTransactionRepository,
        user_repo: AbstractUserRepository,
    ) -> None:
        self._tx_repo = transaction_repo
        self._user_repo = user_repo

    async def execute(self, user_id: int) -> BalanceResult:
        far_past = datetime(2000, 1, 1, tzinfo=timezone.utc)
        now = datetime.now(timezone.utc)
        income = await self._tx_repo.sum_by_period(user_id, far_past, now, TransactionType.INCOME)
        expense = await self._tx_repo.sum_by_period(user_id, far_past, now, TransactionType.EXPENSE)
        savings = await self._tx_repo.sum_by_period(user_id, far_past, now, TransactionType.SAVINGS)
        balance = await self._user_repo.get_balance(user_id)
        return BalanceResult(
            total_income=income,
            total_expense=expense,
            total_savings=savings,
            cash_balance=balance.cash_balance if balance else Decimal("0"),
            card_balance=balance.card_balance if balance else Decimal("0"),
            currency_balance=balance.currency_balance if balance else Decimal("0"),
            total_balance=balance.total_balance if balance else Decimal("0"),
        )
