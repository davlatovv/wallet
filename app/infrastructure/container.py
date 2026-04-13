"""
Dependency Injection container.
Usage in handlers:
    container = request.bot.get("container")
    use_case = container.add_expense_use_case(session)
"""
from sqlalchemy.ext.asyncio import AsyncSession

from app.application.use_cases.analytics.get_report import GetReportUseCase
from app.application.use_cases.budgets.manage_budgets import (
    SetBudgetUseCase,
    ListBudgetsUseCase,
    DeleteBudgetUseCase,
)
from app.application.use_cases.categories.manage_categories import (
    EnsureUserExistsUseCase,
    ListCategoriesUseCase,
    CreateCategoryUseCase,
    DeleteCategoryUseCase,
)
from app.application.use_cases.debts.manage_debts import (
    AddDebtUseCase,
    SettleDebtUseCase,
    ListDebtsUseCase,
)
from app.application.use_cases.installments.manage_installments import (
    AddInstallmentUseCase,
    PayInstallmentMonthUseCase,
    ListInstallmentsUseCase,
)
from app.application.use_cases.savings.manage_savings import (
    CreateSavingsGoalUseCase,
    AddToSavingsUseCase,
    ListSavingsUseCase,
)
from app.application.use_cases.transactions.add_expense import AddExpenseUseCase
from app.application.use_cases.transactions.add_income import AddIncomeUseCase
from app.application.use_cases.transactions.get_balance import GetBalanceUseCase
from app.infrastructure.db.repositories.budget import SQLAlchemyBudgetRepository
from app.infrastructure.db.repositories.category import SQLAlchemyCategoryRepository
from app.infrastructure.db.repositories.debt import SQLAlchemyDebtRepository
from app.infrastructure.db.repositories.installment import SQLAlchemyInstallmentRepository
from app.infrastructure.db.repositories.savings import SQLAlchemySavingsRepository
from app.infrastructure.db.repositories.transaction import SQLAlchemyTransactionRepository
from app.infrastructure.db.repositories.user import SQLAlchemyUserRepository


class Container:
    """Assembles use cases with their dependencies for a given session."""

    def __init__(self, session: AsyncSession) -> None:
        self._session = session
        # Repositories
        self._user_repo = SQLAlchemyUserRepository(session)
        self._tx_repo = SQLAlchemyTransactionRepository(session)
        self._cat_repo = SQLAlchemyCategoryRepository(session)
        self._budget_repo = SQLAlchemyBudgetRepository(session)
        self._debt_repo = SQLAlchemyDebtRepository(session)
        self._savings_repo = SQLAlchemySavingsRepository(session)
        self._inst_repo = SQLAlchemyInstallmentRepository(session)

    # ── Transactions ──────────────────────────────────────────────────────────
    @property
    def add_expense(self) -> AddExpenseUseCase:
        return AddExpenseUseCase(self._tx_repo, self._budget_repo)

    @property
    def add_income(self) -> AddIncomeUseCase:
        return AddIncomeUseCase(self._tx_repo)

    @property
    def get_balance(self) -> GetBalanceUseCase:
        return GetBalanceUseCase(self._tx_repo)

    # ── Categories ────────────────────────────────────────────────────────────
    @property
    def ensure_user(self) -> EnsureUserExistsUseCase:
        return EnsureUserExistsUseCase(self._user_repo, self._cat_repo)

    @property
    def list_categories(self) -> ListCategoriesUseCase:
        return ListCategoriesUseCase(self._cat_repo)

    @property
    def create_category(self) -> CreateCategoryUseCase:
        return CreateCategoryUseCase(self._cat_repo)

    @property
    def delete_category(self) -> DeleteCategoryUseCase:
        return DeleteCategoryUseCase(self._cat_repo)

    # ── Budgets ───────────────────────────────────────────────────────────────
    @property
    def set_budget(self) -> SetBudgetUseCase:
        return SetBudgetUseCase(self._budget_repo)

    @property
    def list_budgets(self) -> ListBudgetsUseCase:
        return ListBudgetsUseCase(self._budget_repo)

    @property
    def delete_budget(self) -> DeleteBudgetUseCase:
        return DeleteBudgetUseCase(self._budget_repo)

    # ── Analytics ─────────────────────────────────────────────────────────────
    @property
    def get_report(self) -> GetReportUseCase:
        return GetReportUseCase(self._tx_repo)

    # ── Debts ─────────────────────────────────────────────────────────────────
    @property
    def add_debt(self) -> AddDebtUseCase:
        return AddDebtUseCase(self._debt_repo)

    @property
    def settle_debt(self) -> SettleDebtUseCase:
        return SettleDebtUseCase(self._debt_repo)

    @property
    def list_debts(self) -> ListDebtsUseCase:
        return ListDebtsUseCase(self._debt_repo)

    # ── Savings ───────────────────────────────────────────────────────────────
    @property
    def create_savings_goal(self) -> CreateSavingsGoalUseCase:
        return CreateSavingsGoalUseCase(self._savings_repo)

    @property
    def add_to_savings(self) -> AddToSavingsUseCase:
        return AddToSavingsUseCase(self._savings_repo)

    @property
    def list_savings(self) -> ListSavingsUseCase:
        return ListSavingsUseCase(self._savings_repo)

    # ── Installments ──────────────────────────────────────────────────────────
    @property
    def add_installment(self) -> AddInstallmentUseCase:
        return AddInstallmentUseCase(self._inst_repo)

    @property
    def pay_installment_month(self) -> PayInstallmentMonthUseCase:
        return PayInstallmentMonthUseCase(self._inst_repo)

    @property
    def list_installments(self) -> ListInstallmentsUseCase:
        return ListInstallmentsUseCase(self._inst_repo)
