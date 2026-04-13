import logging
from datetime import datetime, timezone

from app.application.dto.transaction import AddTransactionDTO
from app.config.settings import settings
from app.domain.entities.budget import BudgetPeriod
from app.domain.entities.transaction import TransactionEntity, TransactionType
from app.domain.repositories.abstract_budget import AbstractBudgetRepository
from app.domain.repositories.abstract_transaction import AbstractTransactionRepository

logger = logging.getLogger(__name__)

PERIOD_DAYS = {
    BudgetPeriod.DAILY: 1,
    BudgetPeriod.WEEKLY: 7,
    BudgetPeriod.MONTHLY: 30,
}


class BudgetAlert:
    def __init__(self, budget_id: int, category_name: str | None, used_ratio: float, limit: str) -> None:
        self.budget_id = budget_id
        self.category_name = category_name
        self.used_ratio = used_ratio
        self.limit = limit
        self.is_critical = used_ratio >= float(settings.budget_critical_threshold)
        self.is_warning = used_ratio >= float(settings.budget_warn_threshold)


class AddExpenseResult:
    def __init__(self, transaction: TransactionEntity, alerts: list[BudgetAlert]) -> None:
        self.transaction = transaction
        self.alerts = alerts


class AddExpenseUseCase:
    def __init__(
        self,
        transaction_repo: AbstractTransactionRepository,
        budget_repo: AbstractBudgetRepository,
    ) -> None:
        self._tx_repo = transaction_repo
        self._budget_repo = budget_repo

    async def execute(self, dto: AddTransactionDTO) -> AddExpenseResult:
        transaction = await self._tx_repo.create(
            user_id=dto.user_id,
            amount=dto.amount,
            transaction_type=TransactionType.EXPENSE,
            category_id=dto.category_id,
            note=dto.note,
        )
        logger.info("Expense created: user=%d amount=%s", dto.user_id, dto.amount)

        alerts = await self._check_budgets(dto)
        return AddExpenseResult(transaction=transaction, alerts=alerts)

    async def _check_budgets(self, dto: AddTransactionDTO) -> list[BudgetAlert]:
        if not dto.category_id:
            return []
        budgets = await self._budget_repo.list_by_user(dto.user_id)
        relevant = [b for b in budgets if b.category_id == dto.category_id or b.category_id is None]
        alerts: list[BudgetAlert] = []
        now = datetime.now(timezone.utc)
        for budget in relevant:
            from_dt = self._period_start(budget.period, now)
            spent = await self._tx_repo.sum_by_period(
                user_id=dto.user_id,
                from_dt=from_dt,
                to_dt=now,
                transaction_type=TransactionType.EXPENSE,
            )
            ratio = budget.usage_ratio(spent)
            if ratio >= settings.budget_warn_threshold:
                alerts.append(
                    BudgetAlert(
                        budget_id=budget.id,
                        category_name=budget.category_name,
                        used_ratio=float(ratio),
                        limit=str(budget.limit_amount),
                    )
                )
        return alerts

    @staticmethod
    def _period_start(period: BudgetPeriod, now: datetime) -> datetime:
        from datetime import timedelta
        delta = timedelta(days=PERIOD_DAYS.get(period, 30))
        return now - delta
