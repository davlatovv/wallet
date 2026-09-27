from decimal import Decimal

import httpx
import pytest

from app.application.use_cases.debts.manage_debts import (
    AddDebtUseCase, DeleteDebtUseCase, ListDebtsUseCase, SettleDebtUseCase,
)
from app.application.use_cases.savings.manage_savings import (
    AddToSavingsUseCase, CreateSavingsGoalUseCase, ListSavingsUseCase,
)
from app.domain.entities.transaction import TransactionType
from app.presentation.api.deps import get_container
from app.presentation.api.main import create_app
from tests.api.helpers import make_init_data
from tests.fakes import FakeTransactionRepo, FakeUserRepo, MemDebtRepo, MemSavingsRepo

V1 = "/api/v1"


async def _noop(**_):
    return True


class Wired:
    def __init__(self) -> None:
        self.debts, self.goals = MemDebtRepo(), MemSavingsRepo()
        self.txs, self.users = FakeTransactionRepo(), FakeUserRepo()

    ensure_user = property(lambda s: type("E", (), {"execute": staticmethod(_noop)})())
    add_debt = property(lambda s: AddDebtUseCase(s.debts))
    settle_debt = property(lambda s: SettleDebtUseCase(s.debts))
    list_debts = property(lambda s: ListDebtsUseCase(s.debts))
    delete_debt = property(lambda s: DeleteDebtUseCase(s.debts))
    create_savings_goal = property(lambda s: CreateSavingsGoalUseCase(s.goals))
    add_to_savings = property(lambda s: AddToSavingsUseCase(s.goals, s.txs, s.users))
    list_savings = property(lambda s: ListSavingsUseCase(s.goals))


@pytest.fixture
def wired(): return Wired()


@pytest.fixture
async def client(wired):
    app = create_app()
    app.dependency_overrides[get_container] = lambda: wired
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c


async def _h(client, uid=42):
    r = await client.post(f"{V1}/auth/telegram", json={"initData": make_init_data(uid)})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.parametrize("method,path", [
    ("get", "/debts"), ("post", "/debts"), ("post", "/debts/1/settle"), ("delete", "/debts/1"),
    ("get", "/savings"), ("post", "/savings"), ("post", "/savings/1/deposit"),
])
async def test_require_auth(client, method, path):
    assert (await getattr(client, method)(V1 + path)).status_code == 401


# ── debts ───────────────────────────────────────────────────────────────────
DEBT = {"counterparty": " Ali ", "amount": "150000", "debt_type": "i_owe"}


async def test_debt_lifecycle(client):
    h = await _h(client)
    r = await client.post(f"{V1}/debts", headers=h, json={**DEBT, "due_date": "2026-12-01"})
    d = r.json()
    assert r.status_code == 201 and d["counterparty"] == "Ali" and d["amount"] == "150000.00" \
        and d["status"] == "active" and d["due_date"] == "2026-12-01"
    await client.post(f"{V1}/debts", headers=h, json={**DEBT, "debt_type": "owed_to_me"})
    assert len((await client.get(f"{V1}/debts", headers=h)).json()) == 2
    s = await client.post(f"{V1}/debts/{d['id']}/settle", headers=h)
    assert s.json()["status"] == "settled"
    active = (await client.get(f"{V1}/debts?status=active", headers=h)).json()
    assert [x["debt_type"] for x in active] == ["owed_to_me"]
    assert (await client.delete(f"{V1}/debts/{d['id']}", headers=h)).status_code == 204
    assert len((await client.get(f"{V1}/debts", headers=h)).json()) == 1


@pytest.mark.parametrize("patch", [
    {"counterparty": ""}, {"counterparty": "x" * 129}, {"amount": "0"}, {"amount": "-1"},
    {"debt_type": "gift"}, {"due_date": "not-a-date"},
])
async def test_debt_validation(client, patch):
    h = await _h(client)
    assert (await client.post(f"{V1}/debts", headers=h, json={**DEBT, **patch})).status_code == 422


async def test_debts_are_private_per_user(client):
    owner, other = await _h(client, 1), await _h(client, 2)
    did = (await client.post(f"{V1}/debts", headers=owner, json=DEBT)).json()["id"]
    assert (await client.get(f"{V1}/debts", headers=other)).json() == []
    assert (await client.post(f"{V1}/debts/{did}/settle", headers=other)).status_code == 404
    assert (await client.delete(f"{V1}/debts/{did}", headers=other)).status_code == 404
    assert (await client.get(f"{V1}/debts", headers=owner)).json()[0]["status"] == "active"


# ── savings ─────────────────────────────────────────────────────────────────
GOAL = {"name": "Laptop", "target_amount": "1000"}


async def test_goal_deposit_updates_progress_balance_and_records_transaction(client, wired):
    h = await _h(client)
    g = (await client.post(f"{V1}/savings", headers=h, json=GOAL)).json()
    assert (g["current_amount"], g["remaining"], g["progress_percent"]) == ("0.00", "1000.00", 0)
    r = await client.post(f"{V1}/savings/{g['id']}/deposit", headers=h, json={"amount": "250"})
    assert r.status_code == 200
    assert (r.json()["current_amount"], r.json()["progress_percent"], r.json()["status"]) == ("250.00", 25, "active")
    assert (await wired.users.get_balance(42)).card_balance == Decimal("-250")
    assert [t.transaction_type for t in wired.txs.items] == [TransactionType.SAVINGS]


async def test_reaching_target_completes_goal_and_closes_deposits(client):
    h = await _h(client)
    gid = (await client.post(f"{V1}/savings", headers=h, json=GOAL)).json()["id"]
    r = await client.post(f"{V1}/savings/{gid}/deposit", headers=h, json={"amount": "1000"})
    assert (r.json()["status"], r.json()["progress_percent"]) == ("completed", 100)
    again = await client.post(f"{V1}/savings/{gid}/deposit", headers=h, json={"amount": "1"})
    assert again.status_code == 409 and again.json()["code"] == "business_rule_violation"


async def test_deposit_validation_and_isolation(client, wired):
    owner, other = await _h(client, 1), await _h(client, 2)
    gid = (await client.post(f"{V1}/savings", headers=owner, json=GOAL)).json()["id"]
    for bad in ({"amount": "0"}, {"amount": "-5"}, {}, {"amount": "x"}):
        assert (await client.post(f"{V1}/savings/{gid}/deposit", headers=owner, json=bad)).status_code == 422
    r = await client.post(f"{V1}/savings/{gid}/deposit", headers=other, json={"amount": "5"})
    assert r.status_code == 404
    assert wired.txs.items == [] and (await client.get(f"{V1}/savings", headers=other)).json() == []


@pytest.mark.parametrize("patch", [{"name": ""}, {"name": "x" * 129}, {"target_amount": "0"},
                                   {"deadline": "soon"}])
async def test_goal_validation(client, patch):
    h = await _h(client)
    assert (await client.post(f"{V1}/savings", headers=h, json={**GOAL, **patch})).status_code == 422


async def test_active_only_filter(client):
    h = await _h(client)
    done = (await client.post(f"{V1}/savings", headers=h, json={"name": "A", "target_amount": "10"})).json()["id"]
    await client.post(f"{V1}/savings", headers=h, json={"name": "B", "target_amount": "10"})
    await client.post(f"{V1}/savings/{done}/deposit", headers=h, json={"amount": "10"})
    assert len((await client.get(f"{V1}/savings", headers=h)).json()) == 2
    assert [g["name"] for g in (await client.get(f"{V1}/savings?active_only=true", headers=h)).json()] == ["B"]
