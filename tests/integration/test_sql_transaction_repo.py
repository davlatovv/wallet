"""SQLAlchemy transaction repository against in-memory SQLite (no Postgres needed).
`FOR UPDATE` is a no-op on SQLite, so row locking itself is not covered here."""
from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.domain.entities.transaction import AccountType, TransactionType
from app.infrastructure.db.models.base import Base
from app.infrastructure.db.models import category, transaction, user  # noqa: F401  (register tables)
from app.infrastructure.db.models.category import Category
from app.infrastructure.db.models.user import User
from app.infrastructure.db.repositories.transaction import SQLAlchemyTransactionRepository
from app.infrastructure.db.repositories.user import SQLAlchemyUserRepository

from tests.fakes import FakeRateProvider

D = Decimal


async def _add_category(session, user_id, name):
    c = Category(user_id=user_id, name=name, category_type="expense", is_system=False)
    session.add(c)
    await session.flush()
    return c.id


async def test_list_page_cursor_filters_and_category_name(session):
    repo = SQLAlchemyTransactionRepository(session)
    cat = await _add_category(session, 1, "Food")
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(5):
        tx = await repo.create(1, D(i + 1), TransactionType.EXPENSE, cat if i % 2 else None, None)
        await repo.update(tx.id, 1, {"created_at": base})  # identical timestamps: id breaks ties
    await repo.create(2, D("9"), TransactionType.EXPENSE, None, None)

    p1 = await repo.list_page(1, limit=3)
    assert [t.id for t in p1] == [5, 4, 3]
    assert p1[1].category_name == "Food" and p1[0].category_name is None
    p2 = await repo.list_page(1, limit=3, before=(p1[-1].created_at, p1[-1].id))
    assert [t.id for t in p2] == [2, 1]
    assert [t.id for t in await repo.list_page(1, limit=10, category_id=cat)] == [4, 2]


async def test_list_page_hides_other_users_category_names(session):
    repo = SQLAlchemyTransactionRepository(session)
    foreign = await _add_category(session, 2, "Secret")
    await repo.create(1, D("1"), TransactionType.EXPENSE, foreign, None)
    [row] = await repo.list_page(1, limit=10)
    assert row.category_name is None


async def test_update_persists_changes_and_scopes_to_user(session):
    repo = SQLAlchemyTransactionRepository(session)
    tx = await repo.create(1, D("10"), TransactionType.EXPENSE, None, None)
    out = await repo.update(tx.id, 1, {"amount": D("25"), "account_type": AccountType.CASH, "note": "n"})
    assert (out.amount, out.account_type, out.note) == (D("25"), AccountType.CASH, "n")
    assert (await repo.get_by_id(tx.id, 1)).account_type == AccountType.CASH
    assert await repo.update(tx.id, 2, {"amount": D("1")}) is None
    assert (await repo.get_by_id(tx.id, 1)).amount == D("25")


async def test_get_by_id_for_update_and_delete(session):
    repo = SQLAlchemyTransactionRepository(session)
    tx = await repo.create(1, D("10"), TransactionType.INCOME, None, None)
    assert await repo.get_by_id(tx.id, 1, for_update=True) is not None
    assert await repo.delete(tx.id, 2) is False
    assert await repo.delete(tx.id, 1) is True


async def test_full_edit_flow_keeps_user_balance_consistent(session):
    from app.application.dto.transaction import AddTransactionDTO, UpdateTransactionDTO
    from app.application.use_cases.transactions.add_income import AddIncomeUseCase
    from app.application.use_cases.transactions.delete_transaction import DeleteTransactionUseCase
    from app.application.use_cases.transactions.update_transaction import UpdateTransactionUseCase
    from app.infrastructure.db.repositories.category import SQLAlchemyCategoryRepository

    txs, users = SQLAlchemyTransactionRepository(session), SQLAlchemyUserRepository(session)
    inc = await AddIncomeUseCase(txs, users).execute(AddTransactionDTO(user_id=1, amount=D("1000")))
    await UpdateTransactionUseCase(txs, SQLAlchemyCategoryRepository(session), users, FakeRateProvider()).execute(
        UpdateTransactionDTO(user_id=1, transaction_id=inc.id, amount=D("400"), currency="CASH"))
    bal = await users.get_balance(1)
    assert (bal.card_balance, bal.cash_balance, bal.total_balance) == (D("0"), D("400"), D("400"))
    await DeleteTransactionUseCase(txs, users).execute(inc.id, 1)
    bal = await users.get_balance(1)
    assert (bal.cash_balance, bal.total_balance) == (D("0"), D("0"))


async def test_sum_by_period_category_filter(session):
    repo = SQLAlchemyTransactionRepository(session)
    a, b = await _add_category(session, 1, "a"), await _add_category(session, 1, "b")
    for cat, amt in ((a, "10"), (a, "5"), (b, "100"), (None, "1000")):
        await repo.create(1, D(amt), TransactionType.EXPENSE, cat, None)
    lo, hi = datetime(2000, 1, 1, tzinfo=timezone.utc), datetime(2100, 1, 1, tzinfo=timezone.utc)
    total = lambda **kw: repo.sum_by_period(1, lo, hi, TransactionType.EXPENSE, **kw)
    assert await total() == D("1115")
    assert await total(category_id=a) == D("15")
    assert await total(category_id=b) == D("100")


async def test_budget_repo_update_limit_and_scoping(session):
    from datetime import date
    from app.domain.entities.budget import BudgetPeriod
    from app.infrastructure.db.repositories.budget import SQLAlchemyBudgetRepository
    repo = SQLAlchemyBudgetRepository(session)
    cat = await _add_category(session, 1, "food")
    b = await repo.create(1, cat, D("100"), BudgetPeriod.MONTHLY, date.today())
    out = await repo.update_limit(b.id, 1, D("250"))
    assert (out.limit_amount, out.category_name) == (D("250"), "food")
    assert await repo.update_limit(b.id, 2, D("1")) is None
    assert (await repo.get_by_id(b.id, 1)).limit_amount == D("250")


async def test_set_budget_and_categories_against_sql(session):
    from app.application.use_cases.budgets.manage_budgets import SetBudgetUseCase
    from app.application.use_cases.categories.manage_categories import (
        CreateCategoryUseCase, DeleteCategoryUseCase,
    )
    from app.domain.entities.budget import BudgetPeriod
    from app.infrastructure.db.repositories.budget import SQLAlchemyBudgetRepository
    from app.infrastructure.db.repositories.category import SQLAlchemyCategoryRepository
    cats = SQLAlchemyCategoryRepository(session)
    cat = await CreateCategoryUseCase(cats).execute(1, "Pets", "🐶", None, "expense")
    setter = SetBudgetUseCase(SQLAlchemyBudgetRepository(session), cats)
    one = await setter.execute(1, D("10"), BudgetPeriod.WEEKLY, category_id=cat.id)
    two = await setter.execute(1, D("20"), BudgetPeriod.WEEKLY, category_id=cat.id)
    assert one.id == two.id and two.limit_amount == D("20")
    await DeleteCategoryUseCase(cats).execute(cat.id, 1)
    assert await cats.get_by_id(cat.id, 1) is None


async def test_savings_add_funds_is_incremental_and_completes(session):
    from app.domain.entities.savings import SavingsStatus
    from app.infrastructure.db.repositories.savings import SQLAlchemySavingsRepository
    repo = SQLAlchemySavingsRepository(session)
    g = await repo.create(1, "Trip", D("100"), None, None)
    a = await repo.add_funds(g.id, 1, D("40"))
    b = await repo.add_funds(g.id, 1, D("30"))
    assert (a.current_amount, b.current_amount, b.status) == (D("40"), D("70"), SavingsStatus.ACTIVE)
    done = await repo.add_funds(g.id, 1, D("30"))
    assert (done.current_amount, done.status) == (D("100"), SavingsStatus.COMPLETED)
    assert await repo.add_funds(g.id, 2, D("5")) is None
    assert (await repo.get_by_id(g.id, 1)).current_amount == D("100")


async def test_debt_repo_roundtrip_and_scoping(session):
    from app.domain.entities.debt import DebtStatus, DebtType
    from app.infrastructure.db.repositories.debt import SQLAlchemyDebtRepository
    repo = SQLAlchemyDebtRepository(session)
    d = await repo.create(1, "Ali", D("5"), DebtType.I_OWE, None, None)
    assert await repo.settle(d.id, 2) is None or (await repo.get_by_id(d.id, 1)).status == DebtStatus.ACTIVE
    assert (await repo.settle(d.id, 1)).status == DebtStatus.SETTLED
    assert await repo.delete(d.id, 2) is False and await repo.delete(d.id, 1) is True


async def test_user_timezone_get_set_sql(session):
    from app.infrastructure.db.repositories.user import SQLAlchemyUserRepository
    repo = SQLAlchemyUserRepository(session)
    assert await repo.get_timezone(1) == "UTC"
    assert await repo.update_timezone(1, "Asia/Tashkent") == "Asia/Tashkent"
    assert await repo.get_timezone(1) == "Asia/Tashkent"
    assert await repo.update_timezone(999, "UTC") is None
