"""Every error, including framework-generated ones, uses {code, message, details}."""
import httpx
import pytest

from app.config.settings import Settings
from app.presentation.api.main import create_app
from tests.api.helpers import make_init_data

V1 = "/api/v1"


@pytest.fixture
async def client():
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=create_app()),
                                 base_url="http://t") as c:
        yield c


def _assert_shape(body, code):
    assert set(body) == {"code", "message", "details"}, body
    assert body["code"] == code and isinstance(body["message"], str)


async def test_missing_token_is_401_with_standard_body(client):
    r = await client.get(f"{V1}/me")
    assert r.status_code == 401
    _assert_shape(r.json(), "unauthorized")


async def test_bad_token_is_401_with_standard_body(client):
    r = await client.get(f"{V1}/me", headers={"Authorization": "Bearer junk"})
    assert r.status_code == 401
    _assert_shape(r.json(), "unauthorized")


async def test_bad_init_data_is_401_with_standard_body(client):
    r = await client.post(f"{V1}/auth/telegram", json={"initData": make_init_data(1, tamper=True)})
    assert r.status_code == 401
    _assert_shape(r.json(), "unauthorized")


async def test_request_validation_error_has_field_details(client):
    r = await client.post(f"{V1}/auth/telegram", json={})
    assert r.status_code == 422
    body = r.json()
    _assert_shape(body, "validation_error")
    assert body["details"][0]["loc"][-1] == "initData"


async def test_unknown_route_and_wrong_method(client):
    r = await client.get("/api/v1/nope")
    assert r.status_code == 404
    _assert_shape(r.json(), "not_found")
    r = await client.delete(f"{V1}/me")
    assert r.status_code == 405
    _assert_shape(r.json(), "method_not_allowed")


def test_cors_origins_parse_comma_separated(monkeypatch):
    monkeypatch.setenv("CORS_ORIGINS", "https://a.example, https://b.example ,")
    assert Settings().cors_origin_list == ["https://a.example", "https://b.example"]
    monkeypatch.setenv("CORS_ORIGINS", "")
    assert Settings().cors_origin_list == []
