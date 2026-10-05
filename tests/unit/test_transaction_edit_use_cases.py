from datetime import datetime, timedelta, timezone
from decimal import Decimal

import pytest

from app.application.dto.transaction import AddTransactionDTO, UpdateTransactionDTO
from app.application.use_cases.transactions.add_expense import AddExpenseUseCase
from app.application.use_cases.transactions.add_income import AddIncomeUseCase
from app.application.use_cases.transactions.delete_transaction import DeleteTransactionUseCase
from app.application.use_cases.transactions.list_transactions import ListTransactionsUseCase
from app.application.use_cases.transactions.update_transaction import UpdateTransactionUseCase
from app.domain.entities.transaction import AccountType, TransactionType
from app.domain.exceptions.base import BusinessRuleViolation, NotFoundError, ValidationError
from tests.fakes import (
    FakeBudgetRepo, FakeCategoryRepo, FakeRateProvider, FakeTransactionRepo, FakeUserRepo,
)

UID, OTHER = 42, 43
D = Decimal


@pytest.fixture
def txs(): return FakeTransactionRepo()


@pytest.fixture
def users(): return FakeUserRepo()


@pytest.fixture
def cats(): return FakeCategoryRepo({5: UID, 6: OTHER})


async def _expense(txs, users, amount="100", currency="UZS", user=UID, **kw):
    dto = AddTransactionDTO(user_id=user, amount=D(amount), currency=currency, **kw)
    return (await AddExpenseUseCase(txs, FakeBudgetRepo(), users).execute(dto)).transaction


async def _income(txs, users, amount="1000", currency="UZS", user=UID):
    return await AddIncomeUseCase(txs, users).execute(
        AddTransactionDTO(user_id=user, amount=D(amount), currency=currency))


def _upd(txs, cats, users, rates=None):
    return UpdateTransactionUseCase(txs, cats, users, rates or FakeRateProvider())


# ── delete ──────────────────────────────────────────────────────────────────
async def test_delete_expense_restores_balance(txs, users):
    await _income(txs, users, "1000")
    e = await _expense(txs, users, "300")
    await DeleteTransactionUseCase(txs, users).execute(e.id, UID)
    bal = await users.get_balance(UID)
    assert bal.card_balance == D("1000") and bal.total_balance == D("1000")
    assert await txs.get_by_id(e.id, UID) is None


async def test_delete_income_removes_funds(txs, users):
    i = await _income(txs, users, "1000", "CASH")
    await DeleteTransactionUseCase(txs, users).execute(i.id, UID)
    assert (await users.get_balance(UID)).cash_balance == D("0")


async def test_delete_unknown_or_foreign_transaction_is_not_found(txs, users):
    e = await _expense(txs, users, user=OTHER)
    uc = DeleteTransactionUseCase(txs, users)
    with pytest.raises(NotFoundError):
        await uc.execute(e.id, UID)
    with pytest.raises(NotFoundError):
        await uc.execute(9999, UID)
    assert await txs.get_by_id(e.id, OTHER) is not None
    assert (await users.get_balance(OTHER)).card_balance == D("-100")


async def test_savings_transactions_cannot_be_deleted_or_edited(txs, users, cats):
    s = await txs.create(UID, D("50"), TransactionType.SAVINGS, None, "goal")
    with pytest.raises(BusinessRuleViolation):
        await DeleteTransactionUseCase(txs, users).execute(s.id, UID)
    with pytest.raises(BusinessRuleViolation):
        await _upd(txs, cats, users).execute(
            UpdateTransactionDTO(user_id=UID, transaction_id=s.id, amount=D("1")))


# ── update ──────────────────────────────────────────────────────────────────
async def test_update_amount_adjusts_balance_by_difference(txs, users, cats):
    await _income(txs, users, "1000")
    e = await _expense(txs, users, "100")            # card = 900
    out = await _upd(txs, cats, users).execute(
        UpdateTransactionDTO(user_id=UID, transaction_id=e.id, amount=D("250")))
    assert out.amount == D("250.00")
    bal = await users.get_balance(UID)
    assert bal.card_balance == D("750") and bal.total_balance == D("750")


async def test_update_income_amount(txs, users, cats):
    i = await _income(txs, users, "1000")
    await _upd(txs, cats, users).execute(
        UpdateTransactionDTO(user_id=UID, transaction_id=i.id, amount=D("400")))
    assert (await users.get_balance(UID)).total_balance == D("400")


async def test_update_currency_moves_amount_between_accounts(txs, users, cats):
    e = await _expense(txs, users, "100")            # card -100
    out = await _upd(txs, cats, users).execute(
        UpdateTransactionDTO(user_id=UID, transaction_id=e.id, currency="CASH"))
    assert out.account_type == AccountType.CASH
    bal = await users.get_balance(UID)
    assert (bal.card_balance, bal.cash_balance, bal.total_balance) == (D("0"), D("-100"), D("-100"))


async def test_update_leaving_usd_clears_conversion_data(txs, users, cats):
    e = await _expense(txs, users, "125000", "USD", original_amount=D("10"), usd_rate=D("12500"))
    out = await _upd(txs, cats, users).execute(
        UpdateTransactionDTO(user_id=UID, transaction_id=e.id, currency="UZS"))
    assert out.original_amount is None and out.usd_rate is None
    assert out.account_type == AccountType.CARD


async def test_note_only_update_leaves_balance_alone(txs, users, cats):
    e = await _expense(txs, users, "100")
    before = await users.get_balance(UID)
    out = await _upd(txs, cats, users).execute(
        UpdateTransactionDTO(user_id=UID, transaction_id=e.id, note="lunch"))
    assert out.note == "lunch" and await users.get_balance(UID) == before


async def test_explicit_null_clears_category_but_omitted_keeps_it(txs, users, cats):
    e = await _expense(txs, users, "100", category_id=5)
    uc = _upd(txs, cats, users)
    kept = await uc.execute(UpdateTransactionDTO(user_id=UID, transaction_id=e.id, note="x"))
    assert kept.category_id == 5
    cleared = await uc.execute(
        UpdateTransactionDTO(user_id=UID, transaction_id=e.id, category_id=None))
    assert cleared.category_id is None


async def test_cannot_assign_another_users_category(txs, users, cats):
    e = await _expense(txs, users, "100")
    with pytest.raises(NotFoundError):
        await _upd(txs, cats, users).execute(
            UpdateTransactionDTO(user_id=UID, transaction_id=e.id, category_id=6))
    assert (await txs.get_by_id(e.id, UID)).category_id is None


async def test_cannot_update_foreign_transaction(txs, users, cats):
    e = await _expense(txs, users, "100", user=OTHER)
    with pytest.raises(NotFoundError):
        await _upd(txs, cats, users).execute(
            UpdateTransactionDTO(user_id=UID, transaction_id=e.id, amount=D("1")))
    assert (await txs.get_by_id(e.id, OTHER)).amount == D("100.00")


@pytest.mark.parametrize("field", ["amount", "currency", "created_at"])
async def test_required_fields_cannot_be_nulled(txs, users, cats, field):
    e = await _expense(txs, users, "100")
    with pytest.raises(ValidationError):
        await _upd(txs, cats, users).execute(
            UpdateTransactionDTO(user_id=UID, transaction_id=e.id, **{field: None}))


def test_update_dto_validates_amount_and_currency():
    with pytest.raises(Exception):
        UpdateTransactionDTO(user_id=1, transaction_id=1, amount=D("0"))
    with pytest.raises(Exception):
        UpdateTransactionDTO(user_id=1, transaction_id=1, currency="EUR")


# ── list ────────────────────────────────────────────────────────────────────
async def _seed(txs, n):
    base = datetime(2026, 1, 1, tzinfo=timezone.utc)
    for i in range(n):
        tx = await txs.create(UID, D(i + 1), TransactionType.EXPENSE, None, None)
        txs.items[-1] = type(tx)(**{**tx.__dict__, "created_at": base + timedelta(hours=i)})


async def test_list_paginates_newest_first_without_gaps_or_dupes(txs):
    await _seed(txs, 7)
    uc = ListTransactionsUseCase(txs)
    seen, cursor = [], None
    while True:
        page = await uc.execute(UID, limit=3, cursor=cursor)
        seen += [t.id for t in page.items]
        cursor = page.next_cursor
        if cursor is None:
            break
    assert seen == [7, 6, 5, 4, 3, 2, 1]


async def test_list_exact_page_has_no_next_cursor(txs):
    await _seed(txs, 3)
    page = await ListTransactionsUseCase(txs).execute(UID, limit=3)
    assert len(page.items) == 3 and page.next_cursor is None


async def test_list_filters_and_user_isolation(txs, users):
    await _income(txs, users, "10")
    await _expense(txs, users, "5")
    await _expense(txs, users, "7", user=OTHER)
    uc = ListTransactionsUseCase(txs)
    only_income = await uc.execute(UID, transaction_type=TransactionType.INCOME)
    assert [t.transaction_type for t in only_income.items] == [TransactionType.INCOME]
    assert all(t.user_id == UID for t in (await uc.execute(UID)).items)


@pytest.mark.parametrize("kwargs", [{"limit": 0}, {"limit": 101}, {"cursor": "garbage!!"}])
async def test_list_rejects_bad_input(txs, kwargs):
    with pytest.raises(ValidationError):
        await ListTransactionsUseCase(txs).execute(UID, **kwargs)


# ── USD handling on edit ────────────────────────────────────────────────────
async def _usd_expense(txs, users):  # 10 USD @ 12000 = 120000 UZS
    return await _expense(txs, users, "120000", "USD", original_amount=D("10"), usd_rate=D("12000"))


async def test_editing_usd_amount_keeps_historical_rate(txs, users, cats):
    e = await _usd_expense(txs, users)                     # currency acct = -120000
    rates = FakeRateProvider("13000")
    out = await _upd(txs, cats, users, rates).execute(
        UpdateTransactionDTO(user_id=UID, transaction_id=e.id, amount=D("20")))
    assert (out.original_amount, out.usd_rate, out.amount) == (D("20"), D("12000"), D("240000"))
    assert rates.calls == 0
    assert (await users.get_balance(UID)).currency_balance == D("-240000")


async def test_switching_into_usd_uses_current_rate_and_requires_amount(txs, users, cats):
    e = await _expense(txs, users, "100")
    uc = _upd(txs, cats, users, FakeRateProvider("12500"))
    with pytest.raises(ValidationError):
        await uc.execute(UpdateTransactionDTO(user_id=UID, transaction_id=e.id, currency="USD"))
    out = await uc.execute(
        UpdateTransactionDTO(user_id=UID, transaction_id=e.id, currency="USD", amount=D("2")))
    assert (out.amount, out.usd_rate, out.account_type) == (D("25000"), D("12500"), AccountType.CURRENCY)
    bal = await users.get_balance(UID)
    assert (bal.card_balance, bal.currency_balance) == (D("0"), D("-25000"))


async def test_rate_outage_on_edit_is_a_clean_error(txs, users, cats):
    e = await _expense(txs, users, "100")
    from app.domain.exceptions.base import ExternalServiceError
    with pytest.raises(ExternalServiceError):
        await _upd(txs, cats, users, FakeRateProvider(fail=True)).execute(
            UpdateTransactionDTO(user_id=UID, transaction_id=e.id, currency="USD", amount=D("1")))
    assert (await txs.get_by_id(e.id, UID)).currency == "UZS"


# ── timezone handling ───────────────────────────────────────────────────────
async def test_naive_created_at_on_edit_is_treated_as_utc(txs, users, cats):
    e = await _expense(txs, users, "100")
    out = await _upd(txs, cats, users).execute(UpdateTransactionDTO(
        user_id=UID, transaction_id=e.id, created_at=datetime(2026, 1, 1, 12, 0)))
    assert out.created_at == datetime(2026, 1, 1, 12, 0, tzinfo=timezone.utc)


async def test_naive_filters_and_cursor_are_normalised(txs):
    from app.application.use_cases.transactions.list_transactions import decode_cursor, encode_cursor
    uc = ListTransactionsUseCase(txs)
    await uc.execute(UID, from_dt=datetime(2026, 1, 1), to_dt=datetime(2026, 12, 31))  # must not raise
    naive = encode_cursor(datetime(2026, 1, 1, 8, 0), 5)
    created, tx_id = decode_cursor(naive)
    assert created.tzinfo is not None and tx_id == 5
