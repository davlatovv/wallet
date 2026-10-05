from datetime import date, datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.application.dto.transaction import AddTransactionDTO
from app.application.use_cases.budgets.manage_budgets import (
    DeleteBudgetUseCase, GetBudgetProgressUseCase, SetBudgetUseCase,
)
from app.application.use_cases.transactions.add_expense import AddExpenseUseCase
from app.domain.entities.budget import BudgetPeriod
from app.domain.entities.transaction import TransactionType
from app.domain.exceptions.base import NotFoundError, ValidationError
from tests.fakes import FakeBudgetRepo, FakeTransactionRepo, FakeUserRepo, MemCategoryRepo

D = Decimal
U = 1


@pytest.fixture
def cats():
    r = MemCategoryRepo()
    r.add(U, "food")      # id 1
    r.add(U, "fun")       # id 2
    r.add(2, "foreign")   # id 3
    return r


async def test_set_budget_creates_then_upserts_same_category_and_period(cats):
    repo = FakeBudgetRepo()
    uc = SetBudgetUseCase(repo, cats)
    first = await uc.execute(U, D("100"), BudgetPeriod.MONTHLY, category_id=1)
    again = await uc.execute(U, D("250"), BudgetPeriod.MONTHLY, category_id=1)
    assert again.id == first.id and again.limit_amount == D("250") and len(repo.budgets) == 1
    await uc.execute(U, D("50"), BudgetPeriod.WEEKLY, category_id=1)   # other period → new
    await uc.execute(U, D("50"), BudgetPeriod.MONTHLY, category_id=None)  # overall → new
    assert len(repo.budgets) == 3


async def test_set_budget_validation(cats):
    uc = SetBudgetUseCase(FakeBudgetRepo(), cats)
    with pytest.raises(ValidationError):
        await uc.execute(U, D("0"), BudgetPeriod.DAILY)
    with pytest.raises(NotFoundError):
        await uc.execute(U, D("10"), BudgetPeriod.DAILY, category_id=3)   # foreign
    with pytest.raises(NotFoundError):
        await uc.execute(U, D("10"), BudgetPeriod.DAILY, category_id=99)


async def test_delete_budget_scoped_to_user(cats):
    repo = FakeBudgetRepo()
    b = await SetBudgetUseCase(repo, cats).execute(U, D("10"), BudgetPeriod.DAILY)
    with pytest.raises(NotFoundError):
        await DeleteBudgetUseCase(repo).execute(b.id, 2)
    await DeleteBudgetUseCase(repo).execute(b.id, U)
    assert repo.budgets == []


async def _expense(txs, amount, category_id, age_days=0):
    tx = await txs.create(U, D(amount), TransactionType.EXPENSE, category_id, None)
    at = datetime.now(timezone.utc) - timedelta(days=age_days, seconds=1)
    txs.items[-1] = type(tx)(**{**tx.__dict__, "created_at": at})


async def test_progress_counts_only_that_categorys_spending_in_window(cats):
    repo, txs = FakeBudgetRepo(), FakeTransactionRepo()
    setter = SetBudgetUseCase(repo, cats)
    await setter.execute(U, D("100"), BudgetPeriod.WEEKLY, category_id=1)
    await setter.execute(U, D("1000"), BudgetPeriod.WEEKLY, category_id=None)
    await _expense(txs, "80", 1)
    await _expense(txs, "500", 2)             # other category: not in food budget
    await _expense(txs, "999", 1, age_days=10)  # outside 7-day window
    food, overall = await GetBudgetProgressUseCase(repo, txs).execute(U)
    assert (food.spent, food.ratio, food.is_warning, food.is_critical) == (D("80"), D("0.8"), True, False)
    assert (overall.spent, overall.is_warning) == (D("580"), False)


async def test_progress_critical_at_limit(cats):
    repo, txs = FakeBudgetRepo(), FakeTransactionRepo()
    await SetBudgetUseCase(repo, cats).execute(U, D("100"), BudgetPeriod.DAILY, category_id=1)
    await _expense(txs, "100", 1)
    [p] = await GetBudgetProgressUseCase(repo, txs).execute(U)
    assert p.is_critical


async def test_expense_alert_is_scoped_to_budget_category(cats):
    """Regression: a category budget used to be compared against ALL expenses."""
    repo, txs, users = FakeBudgetRepo(), FakeTransactionRepo(), FakeUserRepo()
    await SetBudgetUseCase(repo, cats).execute(U, D("100"), BudgetPeriod.MONTHLY, category_id=1)
    await _expense(txs, "5000", 2)  # heavy spending elsewhere
    res = await AddExpenseUseCase(txs, repo, users).execute(
        AddTransactionDTO(user_id=U, amount=D("10"), category_id=1))
    assert res.alerts == []
    res = await AddExpenseUseCase(txs, repo, users).execute(
        AddTransactionDTO(user_id=U, amount=D("75"), category_id=1))
    assert len(res.alerts) == 1 and res.alerts[0].is_warning
