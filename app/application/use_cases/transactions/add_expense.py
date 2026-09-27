import logging
from datetime import datetime, timezone

from app.application.dto.transaction import AddTransactionDTO
from app.config.settings import settings
from app.domain.entities.budget import budget_window_start
from app.domain.entities.transaction import TransactionEntity, TransactionType
from app.domain.repositories.abstract_budget import AbstractBudgetRepository
from app.domain.repositories.abstract_category import AbstractCategoryRepository
from app.domain.repositories.abstract_transaction import AbstractTransactionRepository
from app.domain.repositories.abstract_user import AbstractUserRepository
from app.domain.exceptions.base import NotFoundError

logger = logging.getLogger(__name__)

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
        user_repo: AbstractUserRepository,
        category_repo: AbstractCategoryRepository | None = None,
    ) -> None:
        self._tx_repo = transaction_repo
        self._budget_repo = budget_repo
        self._user_repo = user_repo
        self._cat_repo = category_repo

    async def execute(self, dto: AddTransactionDTO) -> AddExpenseResult:
        if dto.category_id is not None and self._cat_repo is not None:
            if await self._cat_repo.get_by_id(dto.category_id, dto.user_id) is None:
                raise NotFoundError(f"Category {dto.category_id} not found")
        transaction = await self._tx_repo.create(
            user_id=dto.user_id,
            amount=dto.amount,
            transaction_type=TransactionType.EXPENSE,
            category_id=dto.category_id,
            note=dto.note,
            currency=dto.currency,
            account_type=dto.account_type,
            original_amount=dto.original_amount,
            usd_rate=dto.usd_rate,
        )
        await self._user_repo.apply_balance_delta(dto.user_id, dto.account_type, -dto.amount)
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
            spent = await self._tx_repo.sum_by_period(
                user_id=dto.user_id,
                from_dt=budget_window_start(budget.period, now),
                to_dt=now,
                transaction_type=TransactionType.EXPENSE,
                category_id=budget.category_id,  # None = overall budget
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
