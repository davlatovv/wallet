"""GET/PATCH /me against real use cases over a fake repo."""
import httpx
import pytest

from app.application.use_cases.transactions.get_balance import GetBalanceUseCase
from app.application.use_cases.users.manage_profile import (
    GetUserTimezoneUseCase, UpdateUserTimezoneUseCase,
)
from app.presentation.api.deps import get_container
from app.presentation.api.main import create_app
from tests.api.helpers import make_init_data
from tests.fakes import FakeTransactionRepo, FakeUserRepo

V1 = "/api/v1"


class Wired:
    def __init__(self) -> None:
        self.users, self.txs = FakeUserRepo(), FakeTransactionRepo()

    @property
    def ensure_user(self):
        async def execute(**kw):
            return await self.users.get_or_create(kw["telegram_id"], kw.get("username"), kw.get("first_name"))
        return type("E", (), {"execute": staticmethod(execute)})()
    get_balance = property(lambda s: GetBalanceUseCase(s.txs, s.users))
    get_user_timezone = property(lambda s: GetUserTimezoneUseCase(s.users))
    update_user_timezone = property(lambda s: UpdateUserTimezoneUseCase(s.users))


@pytest.fixture
def wired(): return Wired()


@pytest.fixture
async def client(wired):
    app = create_app()
    app.dependency_overrides[get_container] = lambda: wired
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c


async def _h(client, uid=1):
    r = await client.post(f"{V1}/auth/telegram", json={"initData": make_init_data(uid)})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_me_defaults_to_utc(client):
    h = await _h(client)
    assert (await client.get(f"{V1}/me", headers=h)).json()["timezone"] == "UTC"


async def test_patch_me_updates_and_persists(client):
    h = await _h(client)
    r = await client.patch(f"{V1}/me", headers=h, json={"timezone": "Asia/Tashkent"})
    assert r.status_code == 200 and r.json()["timezone"] == "Asia/Tashkent"
    assert (await client.get(f"{V1}/me", headers=h)).json()["timezone"] == "Asia/Tashkent"


async def test_patch_me_rejects_unknown_timezone(client):
    h = await _h(client)
    r = await client.patch(f"{V1}/me", headers=h, json={"timezone": "Mars/Phobos"})
    assert r.status_code == 422 and r.json()["code"] == "validation_error"


async def test_patch_me_requires_auth(client):
    assert (await client.patch(f"{V1}/me", json={"timezone": "UTC"})).status_code == 401


async def test_patch_me_is_per_user(client):
    h1, h2 = await _h(client, 1), await _h(client, 2)
    await client.patch(f"{V1}/me", headers=h1, json={"timezone": "Asia/Tashkent"})
    assert (await client.get(f"{V1}/me", headers=h2)).json()["timezone"] == "UTC"
