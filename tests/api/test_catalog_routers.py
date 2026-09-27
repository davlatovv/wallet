"""Categories, budgets and analytics routers with real use cases over in-memory fakes."""
from decimal import Decimal

import httpx
import pytest

from app.application.use_cases.analytics.get_report import GetReportUseCase, ListReportMonthsUseCase
from app.application.use_cases.users.manage_profile import (
    GetUserTimezoneUseCase, UpdateUserTimezoneUseCase,
)
from app.application.use_cases.budgets.manage_budgets import (
    DeleteBudgetUseCase, GetBudgetProgressUseCase, SetBudgetUseCase,
)
from app.application.use_cases.transactions.get_balance import GetBalanceUseCase
from app.application.use_cases.categories.manage_categories import (
    CreateCategoryUseCase, DeleteCategoryUseCase, GetCategoryUseCase, ListAllCategoriesUseCase,
    RenameCategoryUseCase,
)
from app.domain.entities.transaction import TransactionType
from app.presentation.api.deps import get_container
from app.presentation.api.main import create_app
from tests.api.helpers import make_init_data
from tests.fakes import FakeBudgetRepo, FakeTransactionRepo, FakeUserRepo, MemCategoryRepo

V1 = "/api/v1"
ME = 42


async def _noop(**_):
    return True


class Wired:
    def __init__(self) -> None:
        self.cats, self.budgets, self.txs = MemCategoryRepo(), FakeBudgetRepo(), FakeTransactionRepo()
        self.users = FakeUserRepo()

    ensure_user = property(lambda s: type("E", (), {"execute": staticmethod(_noop)})())
    list_all_categories = property(lambda s: ListAllCategoriesUseCase(s.cats))
    create_category = property(lambda s: CreateCategoryUseCase(s.cats))
    get_category = property(lambda s: GetCategoryUseCase(s.cats))
    rename_category = property(lambda s: RenameCategoryUseCase(s.cats))
    delete_category = property(lambda s: DeleteCategoryUseCase(s.cats))
    set_budget = property(lambda s: SetBudgetUseCase(s.budgets, s.cats))
    get_budget_progress = property(lambda s: GetBudgetProgressUseCase(s.budgets, s.txs))
    delete_budget = property(lambda s: DeleteBudgetUseCase(s.budgets))
    get_report = property(lambda s: GetReportUseCase(s.txs))
    list_report_months = property(lambda s: ListReportMonthsUseCase(s.txs))
    get_user_timezone = property(lambda s: GetUserTimezoneUseCase(s.users))
    update_user_timezone = property(lambda s: UpdateUserTimezoneUseCase(s.users))
    get_balance = property(lambda s: GetBalanceUseCase(s.txs, s.users))


@pytest.fixture
def wired(): return Wired()


@pytest.fixture
async def client(wired):
    app = create_app()
    app.dependency_overrides[get_container] = lambda: wired
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c


async def _h(client, uid=ME):
    r = await client.post(f"{V1}/auth/telegram", json={"initData": make_init_data(uid)})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


@pytest.mark.parametrize("method,path", [
    ("get", "/categories"), ("post", "/categories"), ("patch", "/categories/1"),
    ("delete", "/categories/1"), ("get", "/budgets"), ("put", "/budgets"),
    ("delete", "/budgets/1"), ("get", "/analytics/report"), ("get", "/analytics/months"),
])
async def test_require_auth(client, method, path):
    assert (await getattr(client, method)(V1 + path)).status_code == 401


# ── categories ──────────────────────────────────────────────────────────────
async def test_category_crud_roundtrip(client):
    h = await _h(client)
    r = await client.post(f"{V1}/categories", headers=h, json={"name": "Coffee", "icon": "☕"})
    assert r.status_code == 201
    cid = r.json()["id"]
    assert r.json() == {"id": cid, "name": "Coffee", "icon": "☕", "parent_id": None,
                        "is_system": False, "category_type": "expense"}
    assert [c["name"] for c in (await client.get(f"{V1}/categories", headers=h)).json()] == ["Coffee"]
    r = await client.patch(f"{V1}/categories/{cid}", headers=h, json={"name": "Tea"})
    assert r.json()["name"] == "Tea" and r.json()["icon"] == "☕"          # icon kept
    r = await client.patch(f"{V1}/categories/{cid}", headers=h, json={"icon": None})
    assert r.json()["icon"] is None and r.json()["name"] == "Tea"          # icon cleared
    assert (await client.delete(f"{V1}/categories/{cid}", headers=h)).status_code == 204
    assert (await client.get(f"{V1}/categories", headers=h)).json() == []


async def test_category_list_type_filter_and_isolation(client, wired):
    wired.cats.add(ME, "inc", ctype="income"); wired.cats.add(ME, "exp"); wired.cats.add(7, "foreign")
    h = await _h(client)
    assert {c["name"] for c in (await client.get(f"{V1}/categories?type=income", headers=h)).json()} == {"inc"}
    assert len((await client.get(f"{V1}/categories", headers=h)).json()) == 2
    assert (await client.get(f"{V1}/categories?type=nope", headers=h)).status_code == 422


@pytest.mark.parametrize("body", [{}, {"name": ""}, {"name": "x" * 65}, {"name": "a", "category_type": "z"},
                                  {"name": "a", "icon": "123456789"}])
async def test_category_create_validation(client, body):
    h = await _h(client)
    assert (await client.post(f"{V1}/categories", headers=h, json=body)).status_code == 422


async def test_category_system_is_409_and_foreign_is_404(client, wired):
    sys_id = wired.cats.add(ME, "Food", system=True).id
    foreign = wired.cats.add(7, "theirs").id
    h = await _h(client)
    assert (await client.delete(f"{V1}/categories/{sys_id}", headers=h)).status_code == 409
    assert (await client.patch(f"{V1}/categories/{sys_id}", headers=h, json={"name": "x"})).status_code == 409
    for call in (client.delete(f"{V1}/categories/{foreign}", headers=h),
                 client.patch(f"{V1}/categories/{foreign}", headers=h, json={"name": "x"})):
        assert (await call).status_code == 404
    r = await client.post(f"{V1}/categories", headers=h, json={"name": "k", "parent_id": foreign})
    assert r.status_code == 404


# ── budgets ─────────────────────────────────────────────────────────────────
async def test_budget_put_upserts_and_get_reports_progress(client, wired):
    cid = wired.cats.add(ME, "food").id
    h = await _h(client)
    body = {"category_id": cid, "period": "monthly", "limit_amount": "100"}
    first = (await client.put(f"{V1}/budgets", headers=h, json=body)).json()
    second = (await client.put(f"{V1}/budgets", headers=h, json={**body, "limit_amount": "200.50"})).json()
    assert first["id"] == second["id"] and second["limit_amount"] == "200.50"

    await wired.txs.create(ME, Decimal("100.25"), TransactionType.EXPENSE, cid, None)
    [b] = (await client.get(f"{V1}/budgets", headers=h)).json()
    assert (b["spent"], b["is_warning"], b["is_critical"]) == ("100.25", False, False)
    assert b["used_ratio"] == pytest.approx(0.5, abs=0.001)


@pytest.mark.parametrize("body", [
    {"period": "monthly", "limit_amount": "0"}, {"period": "monthly", "limit_amount": "-5"},
    {"period": "yearly", "limit_amount": "5"}, {"limit_amount": "5"}, {"period": "daily"},
])
async def test_budget_put_validation(client, body):
    h = await _h(client)
    assert (await client.put(f"{V1}/budgets", headers=h, json=body)).status_code == 422


async def test_budget_foreign_category_404_and_delete(client, wired):
    foreign = wired.cats.add(7, "theirs").id
    h = await _h(client)
    r = await client.put(f"{V1}/budgets", headers=h,
                         json={"category_id": foreign, "period": "daily", "limit_amount": "1"})
    assert r.status_code == 404
    bid = (await client.put(f"{V1}/budgets", headers=h,
                            json={"period": "daily", "limit_amount": "1"})).json()["id"]
    assert (await client.delete(f"{V1}/budgets/{bid}", headers=await _h(client, 7))).status_code == 404
    assert (await client.delete(f"{V1}/budgets/{bid}", headers=h)).status_code == 204
    assert (await client.get(f"{V1}/budgets", headers=h)).json() == []


# ── analytics ───────────────────────────────────────────────────────────────
@pytest.mark.parametrize("period", ["day", "week", "month", "year"])
async def test_report_periods(client, period):
    h = await _h(client)
    r = await client.get(f"{V1}/analytics/report?period={period}", headers=h)
    body = r.json()
    assert r.status_code == 200 and body["period"] == period
    assert body["total_income"] == "0.00" and body["balance"] == "0.00"
    assert body["expense_by_category"] == []


async def test_report_default_month_and_bad_period(client):
    h = await _h(client)
    assert (await client.get(f"{V1}/analytics/report", headers=h)).json()["period"] == "month"
    assert (await client.get(f"{V1}/analytics/report?period=decade", headers=h)).status_code == 422


async def test_report_uses_the_users_saved_timezone(client, wired):
    h = await _h(client)
    await wired.users.get_or_create(ME, None, None)
    utc_from = (await client.get(f"{V1}/analytics/report?period=day", headers=h)).json()["from_dt"]
    await client.patch(f"{V1}/me", headers=h, json={"timezone": "Asia/Tashkent"})
    tz_from = (await client.get(f"{V1}/analytics/report?period=day", headers=h)).json()["from_dt"]
    assert tz_from != utc_from


async def test_months_endpoint(client, wired):
    async def months(user_id): return [(2026, 9), (2026, 8)]
    wired.txs.list_available_months = months
    h = await _h(client)
    assert (await client.get(f"{V1}/analytics/months", headers=h)).json() == [
        {"year": 2026, "month": 9}, {"year": 2026, "month": 8}]
