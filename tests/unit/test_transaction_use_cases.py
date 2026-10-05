from datetime import date
from decimal import Decimal

import pytest

from app.application.dto.transaction import AddTransactionDTO
from app.application.use_cases.transactions.add_expense import AddExpenseUseCase
from app.application.use_cases.transactions.add_income import AddIncomeUseCase
from app.application.use_cases.transactions.get_balance import GetBalanceUseCase
from app.domain.entities.budget import BudgetEntity, BudgetPeriod
from app.domain.entities.transaction import AccountType, TransactionType
from app.domain.exceptions.base import NotFoundError
from tests.fakes import FakeBudgetRepo, FakeTransactionRepo, FakeUserRepo

UID = 42


def _dto(amount: str, currency: str = "UZS", category_id: int | None = None) -> AddTransactionDTO:
    return AddTransactionDTO(user_id=UID, amount=Decimal(amount), currency=currency,
                             category_id=category_id)


async def test_income_increases_matching_account_and_total():
    txs, users = FakeTransactionRepo(), FakeUserRepo()
    tx = await AddIncomeUseCase(txs, users).execute(_dto("1000", "CASH"))
    bal = await users.get_balance(UID)
    assert tx.transaction_type == TransactionType.INCOME
    assert (bal.cash_balance, bal.card_balance, bal.total_balance) == (
        Decimal("1000"), Decimal("0"), Decimal("1000"))


async def test_expense_decreases_account_balance():
    txs, users, budgets = FakeTransactionRepo(), FakeUserRepo(), FakeBudgetRepo()
    await AddIncomeUseCase(txs, users).execute(_dto("1000"))
    result = await AddExpenseUseCase(txs, budgets, users).execute(_dto("300"))
    bal = await users.get_balance(UID)
    assert result.transaction.account_type == AccountType.CARD
    assert bal.card_balance == Decimal("700")
    assert bal.total_balance == Decimal("700")
    assert result.alerts == []


async def test_expense_in_usd_hits_currency_account():
    txs, users, budgets = FakeTransactionRepo(), FakeUserRepo(), FakeBudgetRepo()
    await AddExpenseUseCase(txs, budgets, users).execute(_dto("50", "USD"))
    assert (await users.get_balance(UID)).currency_balance == Decimal("-50")


async def test_expense_over_budget_warns():
    budget = BudgetEntity(id=1, user_id=UID, category_id=7, limit_amount=Decimal("1000"),
                          period=BudgetPeriod.MONTHLY, start_date=date.today())
    txs, users = FakeTransactionRepo(), FakeUserRepo()
    result = await AddExpenseUseCase(txs, FakeBudgetRepo([budget]), users).execute(
        _dto("900", category_id=7))
    assert len(result.alerts) == 1
    assert result.alerts[0].is_warning and not result.alerts[0].is_critical


async def test_expense_without_category_skips_budget_check():
    budget = BudgetEntity(id=1, user_id=UID, category_id=None, limit_amount=Decimal("1"),
                          period=BudgetPeriod.DAILY, start_date=date.today())
    result = await AddExpenseUseCase(FakeTransactionRepo(), FakeBudgetRepo([budget]),
                                     FakeUserRepo()).execute(_dto("500"))
    assert result.alerts == []


async def test_get_balance_aggregates_totals():
    txs, users, budgets = FakeTransactionRepo(), FakeUserRepo(), FakeBudgetRepo()
    await AddIncomeUseCase(txs, users).execute(_dto("1000"))
    await AddExpenseUseCase(txs, budgets, users).execute(_dto("250"))
    res = await GetBalanceUseCase(txs, users).execute(UID)
    assert res.total_income == Decimal("1000")
    assert res.total_expense == Decimal("250")
    assert res.balance == Decimal("750")


async def test_get_balance_for_unknown_user_is_zero():
    res = await GetBalanceUseCase(FakeTransactionRepo(), FakeUserRepo()).execute(999)
    assert res.total_balance == Decimal("0")


# ── category ownership (shared by bot and API callers) ─────────────────────
async def test_expense_rejects_foreign_category_when_repo_given():
    from tests.fakes import MemCategoryRepo
    cats = MemCategoryRepo()
    foreign = cats.add(999, "theirs").id
    txs, users, budgets = FakeTransactionRepo(), FakeUserRepo(), FakeBudgetRepo()
    uc = AddExpenseUseCase(txs, budgets, users, cats)
    with pytest.raises(NotFoundError):
        await uc.execute(_dto("10", category_id=foreign))
    assert txs.items == []


async def test_income_rejects_foreign_category_when_repo_given():
    from tests.fakes import MemCategoryRepo
    cats = MemCategoryRepo()
    foreign = cats.add(999, "theirs").id
    txs, users = FakeTransactionRepo(), FakeUserRepo()
    with pytest.raises(NotFoundError):
        await AddIncomeUseCase(txs, users, cats).execute(_dto("10", category_id=foreign))
    assert txs.items == []


async def test_own_category_still_allowed_when_repo_given():
    from tests.fakes import MemCategoryRepo
    cats = MemCategoryRepo()
    mine = cats.add(UID, "food").id
    txs, users, budgets = FakeTransactionRepo(), FakeUserRepo(), FakeBudgetRepo()
    result = await AddExpenseUseCase(txs, budgets, users, cats).execute(_dto("10", category_id=mine))
    assert result.transaction.category_id == mine


async def test_without_a_category_repo_check_is_skipped_backward_compat():
    txs, users, budgets = FakeTransactionRepo(), FakeUserRepo(), FakeBudgetRepo()
    result = await AddExpenseUseCase(txs, budgets, users).execute(_dto("10", category_id=999999))
    assert result.transaction.category_id == 999999
