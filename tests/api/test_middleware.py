"""Rate limiting and request logging middleware, at the ASGI level."""
import httpx
import pytest
import structlog

from app.config.settings import settings
from app.presentation.api.deps import get_container
from app.presentation.api.main import create_app
from tests.api.helpers import make_init_data

V1 = "/api/v1"


from app.application.use_cases.transactions.get_balance import GetBalanceUseCase
from app.application.use_cases.users.manage_profile import (
    GetUserTimezoneUseCase, UpdateUserTimezoneUseCase,
)
from tests.fakes import FakeTransactionRepo, FakeUserRepo


async def _noop(**_):
    return True


class _FakeContainer:
    def __init__(self) -> None:
        self.users, self.txs = FakeUserRepo(), FakeTransactionRepo()

    @property
    def ensure_user(self):
        async def execute(**kw):
            return await self.users.get_or_create(kw["telegram_id"], kw.get("username"), kw.get("first_name"))
        return type("E", (), {"execute": staticmethod(execute)})()

    @property
    def get_balance(self):
        return GetBalanceUseCase(self.txs, self.users)

    @property
    def get_user_timezone(self):
        return GetUserTimezoneUseCase(self.users)

    @property
    def update_user_timezone(self):
        return UpdateUserTimezoneUseCase(self.users)


def _fake_container():
    return _FakeContainer()


@pytest.fixture
def low_limit():
    """Applies to the whole app, since create_app() reads settings at call time."""
    orig_n, orig_w = settings.rate_limit_requests, settings.rate_limit_window_seconds
    settings.rate_limit_requests, settings.rate_limit_window_seconds = 3, 60
    yield
    settings.rate_limit_requests, settings.rate_limit_window_seconds = orig_n, orig_w


@pytest.fixture
async def client(low_limit):
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app()),
                                 base_url="http://t") as c:
        yield c


async def test_health_is_exempt_from_rate_limiting(client):
    for _ in range(10):
        assert (await client.get("/health")).status_code == 200


async def test_unauthenticated_requests_share_an_ip_bucket(client):
    for _ in range(3):
        r = await client.get(f"{V1}/me")   # 401 each time, but still consumes the bucket
        assert r.status_code == 401
    blocked = await client.get(f"{V1}/me")
    assert blocked.status_code == 429
    body = blocked.json()
    assert body["code"] == "rate_limited" and "Retry-After" in blocked.headers
    assert int(blocked.headers["Retry-After"]) >= 1


async def test_response_carries_remaining_header(client):
    r = await client.get("/health")  # exempt path: header absent
    assert "x-ratelimit-remaining" not in r.headers
    r = await client.get(f"{V1}/me")
    assert r.headers["x-ratelimit-remaining"] == "2"


async def test_limit_is_per_authenticated_user_not_global(low_limit):
    app = create_app()
    app.dependency_overrides[get_container] = _fake_container
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as client:
        tokens = []
        for uid in (101, 102):
            r = await client.post(f"{V1}/auth/telegram", json={"initData": make_init_data(uid)})
            tokens.append(r.json()["access_token"])
        h1, h2 = {"Authorization": f"Bearer {tokens[0]}"}, {"Authorization": f"Bearer {tokens[1]}"}
        # user1's own "user:101" bucket (limit=3) is independent of the login IP bucket
        await client.get(f"{V1}/me", headers=h1)
        await client.get(f"{V1}/me", headers=h1)
        await client.get(f"{V1}/me", headers=h1)
        assert (await client.get(f"{V1}/me", headers=h1)).status_code == 429
        # user 2's bucket is unaffected
        assert (await client.get(f"{V1}/me", headers=h2)).status_code == 200


async def test_invalid_token_falls_back_to_ip_bucket_not_a_free_pass(client):
    bad = {"Authorization": "Bearer garbage"}
    codes = [(await client.get(f"{V1}/me", headers=bad)).status_code for _ in range(4)]
    assert codes == [401, 401, 401, 429]


async def test_request_is_logged_with_status_and_user(monkeypatch):
    events = []
    monkeypatch.setattr(structlog, "get_logger", lambda *a, **k: _Recorder(events))
    import importlib
    from app.presentation.api import middleware as mw
    importlib.reload(mw)
    from app.presentation.api.main import create_app as _create_app
    app = _create_app()
    app.dependency_overrides[get_container] = _fake_container
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        r = await c.post(f"{V1}/auth/telegram", json={"initData": make_init_data(55)})
        token = r.json()["access_token"]
        await c.get(f"{V1}/me", headers={"Authorization": f"Bearer {token}"})
    importlib.reload(mw)  # restore the real structlog logger for later tests
    assert any(e["path"] == f"{V1}/me" and e["status"] == 200 and e["user_id"] == 55 for e in events)
    assert any(e["path"] == f"{V1}/auth/telegram" and e["status"] == 200 for e in events)


class _Recorder:
    def __init__(self, sink: list) -> None:
        self._sink = sink

    def info(self, event, **kw):
        self._sink.append({"event": event, **kw})
