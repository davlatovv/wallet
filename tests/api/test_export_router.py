import csv
import io

import httpx
import pytest

from app.application.use_cases.export.export_transactions import ExportTransactionsUseCase
from app.infrastructure.db.repositories.transaction import SQLAlchemyTransactionRepository
from app.presentation.api.deps import get_container
from app.presentation.api.main import create_app
from tests.api.helpers import make_init_data
from app.domain.entities.transaction import TransactionType
from decimal import Decimal

V1 = "/api/v1"


async def _noop(**_):
    return True


class Wired:
    def __init__(self, session) -> None:
        self.tx_repo = SQLAlchemyTransactionRepository(session)
        self.ensure_user = type("E", (), {"execute": staticmethod(_noop)})()
        self.export_transactions = ExportTransactionsUseCase(self.tx_repo)


@pytest.fixture
async def client(session):
    app = create_app()
    wired = Wired(session)
    app.dependency_overrides[get_container] = lambda: wired
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c, wired


async def _h(client):
    r = await client.post(f"{V1}/auth/telegram", json={"initData": make_init_data(1)})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


async def test_export_requires_auth(client):
    c, _ = client
    assert (await c.get(f"{V1}/export/transactions")).status_code == 401


async def test_export_csv_download(client):
    c, wired = client
    await wired.tx_repo.create(1, Decimal("10"), TransactionType.INCOME, None, "n")
    h = await _h(c)
    r = await c.get(f"{V1}/export/transactions?format=csv", headers=h)
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "attachment" in r.headers["content-disposition"]
    rows = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig"))))
    assert len(rows) == 2


async def test_export_defaults_to_xlsx(client):
    c, _ = client
    h = await _h(c)
    r = await c.get(f"{V1}/export/transactions", headers=h)
    assert r.status_code == 200 and "spreadsheetml" in r.headers["content-type"]
    assert r.headers["content-disposition"].endswith('.xlsx"')


async def test_export_specific_month_filename(client):
    c, _ = client
    h = await _h(c)
    r = await c.get(f"{V1}/export/transactions?format=csv&month=2026-02-14", headers=h)
    assert 'filename="transactions_2026-02.csv"' in r.headers["content-disposition"]


@pytest.mark.parametrize("qs", ["format=pdf", "month=not-a-date"])
async def test_export_bad_query_is_422(client, qs):
    c, _ = client
    h = await _h(c)
    assert (await c.get(f"{V1}/export/transactions?{qs}", headers=h)).status_code == 422


async def test_export_isolated_per_user(client):
    c, wired = client
    await wired.tx_repo.create(1, Decimal("10"), TransactionType.INCOME, None, "n")
    r2 = await c.post(f"{V1}/auth/telegram", json={"initData": make_init_data(2)})
    h2 = {"Authorization": f"Bearer {r2.json()['access_token']}"}
    r = await c.get(f"{V1}/export/transactions?format=csv", headers=h2)
    rows = list(csv.reader(io.StringIO(r.content.decode("utf-8-sig"))))
    assert len(rows) == 1
