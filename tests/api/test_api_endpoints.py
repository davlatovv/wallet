from decimal import Decimal
from types import SimpleNamespace

import httpx
import pytest

from app.presentation.api.deps import get_container
from app.presentation.api.main import create_app
from app.application.use_cases.transactions.get_balance import BalanceResult
from tests.api.helpers import make_init_data


class _Recorder:
    def __init__(self) -> None:
        self.ensured: list[dict] = []
        self.balance_user_ids: list[int] = []


@pytest.fixture
def rec() -> _Recorder:
    return _Recorder()


@pytest.fixture
async def client(rec: _Recorder):
    async def ensure(**kw):
        rec.ensured.append(kw)
        return True

    async def balance(user_id: int):
        rec.balance_user_ids.append(user_id)
        d = Decimal
        return BalanceResult(d("100"), d("40"), d("0"), d("1.5"), d("58.5"), d("0"), d("60.00"))

    async def get_tz(user_id: int) -> str:
        return "UTC"

    container = SimpleNamespace(
        ensure_user=SimpleNamespace(execute=ensure),
        get_balance=SimpleNamespace(execute=balance),
        get_user_timezone=SimpleNamespace(execute=get_tz),
    )
    app = create_app()
    app.dependency_overrides[get_container] = lambda: container
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c


async def _login(client: httpx.AsyncClient, user_id: int = 42) -> dict[str, str]:
    r = await client.post("/api/v1/auth/telegram", json={"initData": make_init_data(user_id)})
    assert r.status_code == 200, r.text
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_health(client):
    assert (await client.get("/health")).json() == {"status": "ok"}


async def test_login_registers_user_and_returns_token(client, rec):
    await _login(client, 42)
    assert rec.ensured == [{"telegram_id": 42, "username": "ann", "first_name": "Ann"}]


async def test_login_rejects_tampered_init_data(client, rec):
    r = await client.post("/api/v1/auth/telegram",
                          json={"initData": make_init_data(42, tamper=True)})
    assert r.status_code == 401
    assert rec.ensured == []


@pytest.mark.parametrize("path", ["/api/v1/me", "/api/v1/balance"])
async def test_protected_endpoints_require_token(client, path):
    assert (await client.get(path)).status_code == 401
    r = await client.get(path, headers={"Authorization": "Bearer junk"})
    assert r.status_code == 401


async def test_balance_uses_user_from_token_and_serializes_money_as_strings(client, rec):
    headers = await _login(client, 555)
    r = await client.get("/api/v1/balance", headers=headers)
    assert r.status_code == 200
    body = r.json()
    assert rec.balance_user_ids == [555]
    assert body["total_balance"] == "60.00"
    assert body["cash_balance"] == "1.50"


async def test_me(client):
    headers = await _login(client, 9)
    body = (await client.get("/api/v1/me", headers=headers)).json()
    assert body["user_id"] == 9 and body["timezone"] == "UTC"
    assert body["balance"]["total_income"] == "100.00"

