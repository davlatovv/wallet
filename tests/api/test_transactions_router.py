"""Router + real use cases wired to in-memory fakes (no DB)."""
from decimal import Decimal

import httpx
import pytest

from app.application.use_cases.transactions.add_expense import AddExpenseUseCase
from app.application.use_cases.transactions.add_income import AddIncomeUseCase
from app.application.use_cases.transactions.delete_transaction import DeleteTransactionUseCase
from app.application.use_cases.transactions.list_transactions import ListTransactionsUseCase
from app.application.use_cases.transactions.prepare_transaction import PrepareTransactionUseCase
from app.application.use_cases.transactions.update_transaction import UpdateTransactionUseCase
from app.domain.entities.budget import BudgetEntity, BudgetPeriod
from app.presentation.api.deps import get_container
from app.presentation.api.main import create_app
from tests.api.helpers import make_init_data
from tests.fakes import FakeBudgetRepo, FakeCategoryRepo, FakeRateProvider, FakeTransactionRepo, FakeUserRepo

V1 = "/api/v1"


class WiredContainer:
    def __init__(self) -> None:
        self.txs, self.users = FakeTransactionRepo(), FakeUserRepo()
        self.cats = FakeCategoryRepo({5: 42, 6: 43})
        self.rates = FakeRateProvider("12500")
        self.budgets = FakeBudgetRepo()

    prepare_transaction = property(lambda s: PrepareTransactionUseCase(s.cats, s.rates))
    add_expense = property(lambda s: AddExpenseUseCase(s.txs, s.budgets, s.users))
    add_income = property(lambda s: AddIncomeUseCase(s.txs, s.users))
    list_transactions = property(lambda s: ListTransactionsUseCase(s.txs))
    update_transaction = property(lambda s: UpdateTransactionUseCase(s.txs, s.cats, s.users, s.rates))
    delete_transaction = property(lambda s: DeleteTransactionUseCase(s.txs, s.users))
    usd_rates = property(lambda s: s.rates)
    ensure_user = property(lambda s: type("E", (), {"execute": staticmethod(_noop)})())


async def _noop(**_): return True


@pytest.fixture
def wired() -> WiredContainer:
    return WiredContainer()


@pytest.fixture
async def client(wired):
    app = create_app()
    app.dependency_overrides[get_container] = lambda: wired
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c


async def _auth(client, uid=42):
    r = await client.post(f"{V1}/auth/telegram", json={"initData": make_init_data(uid)})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_all_endpoints_require_auth(client):
    for method, path in [("get", "/transactions"), ("post", "/transactions/expense"),
                         ("post", "/transactions/income"), ("patch", "/transactions/1"),
                         ("delete", "/transactions/1"), ("get", "/currency/usd-rate")]:
        assert (await getattr(client, method)(V1 + path)).status_code == 401, path


async def test_create_expense_income_then_list_newest_first(client, wired):
    h = await _auth(client)
    inc = await client.post(f"{V1}/transactions/income", headers=h, json={"amount": "1000"})
    exp = await client.post(f"{V1}/transactions/expense", headers=h,
                            json={"amount": "250.5", "category_id": 5, "note": "food"})
    assert inc.status_code == exp.status_code == 201
    assert exp.json()["transaction"]["amount"] == "250.50" and exp.json()["alerts"] == []
    listing = (await client.get(f"{V1}/transactions", headers=h)).json()
    assert [t["transaction_type"] for t in listing["items"]] == ["expense", "income"]
    assert listing["next_cursor"] is None
    assert (await wired.users.get_balance(42)).card_balance == Decimal("749.50")


async def test_usd_expense_is_converted_server_side(client):
    h = await _auth(client)
    r = await client.post(f"{V1}/transactions/expense", headers=h,
                          json={"amount": "2", "currency": "USD"})
    t = r.json()["transaction"]
    assert (t["amount"], t["original_amount"], t["usd_rate"], t["account_type"]) == (
        "25000.00", "2.00", "12500.00", "currency")


async def test_expense_response_carries_budget_alerts(client, wired):
    from datetime import date
    wired.budgets.budgets = [BudgetEntity(1, 42, 5, Decimal("100"), BudgetPeriod.MONTHLY, date.today(), "Food")]
    h = await _auth(client)
    r = await client.post(f"{V1}/transactions/expense", headers=h,
                          json={"amount": "95", "category_id": 5})
    [alert] = r.json()["alerts"]
    assert alert["is_warning"] and not alert["is_critical"] and alert["category_name"] == "Food"


async def test_pagination_via_query_params(client):
    h = await _auth(client)
    for _ in range(5):
        await client.post(f"{V1}/transactions/income", headers=h, json={"amount": "1"})
    p1 = (await client.get(f"{V1}/transactions?limit=2", headers=h)).json()
    p2 = (await client.get(f"{V1}/transactions?limit=2&cursor={p1['next_cursor']}", headers=h)).json()
    assert [t["id"] for t in p1["items"] + p2["items"]] == [5, 4, 3, 2]
    assert (await client.get(f"{V1}/transactions?type=expense", headers=h)).json()["items"] == []


@pytest.mark.parametrize("qs", ["limit=0", "limit=101", "type=bogus"])
async def test_list_bad_query_is_422(client, qs):
    h = await _auth(client)
    assert (await client.get(f"{V1}/transactions?{qs}", headers=h)).status_code == 422


async def test_bad_cursor_is_422_from_domain_error(client):
    h = await _auth(client)
    r = await client.get(f"{V1}/transactions?cursor=zzz", headers=h)
    assert r.status_code == 422 and r.json()["code"] == "validation_error"


@pytest.mark.parametrize("body", [
    {"amount": "0"}, {"amount": "-1"}, {"amount": "abc"}, {"amount": "1", "currency": "EUR"},
    {"amount": "1", "note": "x" * 501}, {},
])
async def test_create_validation_errors(client, body):
    h = await _auth(client)
    assert (await client.post(f"{V1}/transactions/expense", headers=h, json=body)).status_code == 422


async def test_foreign_category_is_404_and_nothing_is_written(client, wired):
    h = await _auth(client)
    r = await client.post(f"{V1}/transactions/expense", headers=h,
                          json={"amount": "1", "category_id": 6})
    assert r.status_code == 404 and r.json()["code"] == "not_found"
    assert wired.txs.items == []


async def test_rate_outage_is_503(client, wired):
    wired.rates.fail = True
    h = await _auth(client)
    r = await client.post(f"{V1}/transactions/expense", headers=h,
                          json={"amount": "1", "currency": "USD"})
    assert r.status_code == 503 and r.json()["code"] == "service_unavailable"


async def test_patch_partial_update_and_explicit_null_category(client, wired):
    h = await _auth(client)
    tid = (await client.post(f"{V1}/transactions/expense", headers=h,
                             json={"amount": "100", "category_id": 5})).json()["transaction"]["id"]
    r = await client.patch(f"{V1}/transactions/{tid}", headers=h, json={"note": "hi"})
    assert r.json()["note"] == "hi" and r.json()["category_id"] == 5
    r = await client.patch(f"{V1}/transactions/{tid}", headers=h, json={"category_id": None})
    assert r.json()["category_id"] is None
    r = await client.patch(f"{V1}/transactions/{tid}", headers=h, json={"amount": "300"})
    assert r.json()["amount"] == "300.00"
    assert (await wired.users.get_balance(42)).card_balance == Decimal("-300")


async def test_patch_and_delete_other_users_transaction_is_404(client, wired):
    owner, intruder = await _auth(client, 43), await _auth(client, 42)
    tid = (await client.post(f"{V1}/transactions/expense", headers=owner,
                             json={"amount": "100"})).json()["transaction"]["id"]
    assert (await client.patch(f"{V1}/transactions/{tid}", headers=intruder,
                               json={"amount": "1"})).status_code == 404
    assert (await client.delete(f"{V1}/transactions/{tid}", headers=intruder)).status_code == 404
    assert len(wired.txs.items) == 1


async def test_delete_returns_204_and_restores_balance(client, wired):
    h = await _auth(client)
    tid = (await client.post(f"{V1}/transactions/expense", headers=h,
                             json={"amount": "100"})).json()["transaction"]["id"]
    r = await client.delete(f"{V1}/transactions/{tid}", headers=h)
    assert r.status_code == 204 and r.content == b""
    assert (await wired.users.get_balance(42)).total_balance == Decimal("0")
    assert (await client.delete(f"{V1}/transactions/{tid}", headers=h)).status_code == 404


async def test_savings_transaction_is_409(client, wired):
    from app.domain.entities.transaction import TransactionType
    h = await _auth(client)
    s = await wired.txs.create(42, Decimal("5"), TransactionType.SAVINGS, None, "goal")
    assert (await client.delete(f"{V1}/transactions/{s.id}", headers=h)).status_code == 409
    assert (await client.patch(f"{V1}/transactions/{s.id}", headers=h,
                               json={"note": "x"})).status_code == 409


async def test_usd_rate_endpoint(client):
    h = await _auth(client)
    assert (await client.get(f"{V1}/currency/usd-rate", headers=h)).json() == {"rate": "12500.00"}
