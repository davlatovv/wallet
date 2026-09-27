"""Reminders router → real use cases → real repository (SQLite)."""
import httpx
import pytest

from app.application.use_cases.reminders.manage_reminders import (
    CreateCreditReminderUseCase, CreateEducationReminderUseCase, CreateInstallmentReminderUseCase,
    CreateRegularReminderUseCase, DeleteReminderUseCase, GetReminderDetailUseCase,
    ListRemindersUseCase, PreviewCreditUseCase, RecordPaymentUseCase,
)
from app.infrastructure.db.repositories.reminder import SQLAlchemyReminderRepository
from app.presentation.api.deps import get_container
from app.presentation.api.main import create_app
from tests.api.helpers import make_init_data

V1 = "/api/v1"


async def _noop(**_):
    return True


class Wired:
    def __init__(self, session) -> None:
        r = SQLAlchemyReminderRepository(session)
        self.ensure_user = type("E", (), {"execute": staticmethod(_noop)})()
        self.preview_credit = PreviewCreditUseCase()
        self.create_credit_reminder = CreateCreditReminderUseCase(r)
        self.create_installment_reminder = CreateInstallmentReminderUseCase(r)
        self.create_education_reminder = CreateEducationReminderUseCase(r)
        self.create_regular_reminder = CreateRegularReminderUseCase(r)
        self.list_reminders = ListRemindersUseCase(r)
        self.get_reminder_detail = GetReminderDetailUseCase(r)
        self.record_payment = RecordPaymentUseCase(r)
        self.delete_reminder = DeleteReminderUseCase(r)


@pytest.fixture
async def client(session):
    app = create_app()
    wired = Wired(session)
    app.dependency_overrides[get_container] = lambda: wired
    async with httpx.AsyncClient(transport=httpx.ASGITransport(app=app), base_url="http://t") as c:
        yield c


async def _h(client, uid=1):
    r = await client.post(f"{V1}/auth/telegram", json={"initData": make_init_data(uid)})
    return {"Authorization": f"Bearer {r.json()['access_token']}"}


CREDIT = {"name": "Car", "total_amount": "3000", "interest_rate": "12", "months_total": 3,
          "payment_type": "differential", "first_payment_date": "2026-01-31"}
INSTALL = {"name": "Phone", "total_amount": "200", "monthly_payment": "100", "months_total": 2,
           "first_payment_date": "2026-01-05"}
EDU = {"name": "Uni", "total_amount": "5000", "payment_amount": "1000", "first_payment_date": "2026-02-01"}
REG = {"name": "Rent", "payment_amount": "500", "first_payment_date": "2026-01-01"}


@pytest.mark.parametrize("method,path", [
    ("get", "/reminders"), ("post", "/reminders/credit"), ("post", "/reminders/credit/preview"),
    ("post", "/reminders/installment"), ("post", "/reminders/education"), ("post", "/reminders/regular"),
    ("get", "/reminders/1"), ("post", "/reminders/1/payments"), ("delete", "/reminders/1"),
])
async def test_require_auth(client, method, path):
    assert (await getattr(client, method)(V1 + path)).status_code == 401


async def test_create_each_type(client):
    h = await _h(client)
    for kind, body in (("credit", CREDIT), ("installment", INSTALL), ("education", EDU), ("regular", REG)):
        r = await client.post(f"{V1}/reminders/{kind}", headers=h, json=body)
        assert r.status_code == 201, (kind, r.text)
        assert r.json()["reminder_type"] == kind and r.json()["status"] == "active"
    items = (await client.get(f"{V1}/reminders", headers=h)).json()
    assert [i["reminder_type"] for i in items] == ["regular", "installment", "credit", "education"]  # soonest next date first
    assert all(i["payment_schedule"] is None for i in items)


async def test_payment_day_is_derived_from_first_date(client):
    h = await _h(client)
    made = (await client.post(f"{V1}/reminders/regular", headers=h,
                              json={**REG, "first_payment_date": "2026-01-31"})).json()
    r1 = (await client.post(f"{V1}/reminders/{made['id']}/payments", headers=h, json={})).json()
    r2 = (await client.post(f"{V1}/reminders/{made['id']}/payments", headers=h, json={})).json()
    assert (r1["next_payment_date"], r2["next_payment_date"]) == ("2026-02-28", "2026-03-31")


async def test_detail_includes_schedule_and_payment_flow(client):
    h = await _h(client)
    made = (await client.post(f"{V1}/reminders/credit", headers=h, json=CREDIT)).json()
    detail = (await client.get(f"{V1}/reminders/{made['id']}", headers=h)).json()
    sched = detail["payment_schedule"]
    assert [row["month"] for row in sched] == [1, 2, 3] and sched[-1]["balance"] == "0.00"
    assert detail["payment_amount"] == sched[0]["payment"]

    r = await client.post(f"{V1}/reminders/{made['id']}/payments", headers=h, json={})
    body = r.json()
    assert r.status_code == 200 and body["paid_amount"] == sched[0]["payment"]
    assert body["payment_amount"] == sched[1]["payment"] and body["months_paid"] == 1
    assert body["interest_rate"] == "12.00" and body["progress_percent"] is not None


async def test_installment_completes_then_409(client):
    h = await _h(client)
    rid = (await client.post(f"{V1}/reminders/installment", headers=h, json=INSTALL)).json()["id"]
    await client.post(f"{V1}/reminders/{rid}/payments", headers=h, json={})
    last = await client.post(f"{V1}/reminders/{rid}/payments", headers=h, json={})
    assert last.json()["status"] == "completed" and last.json()["remaining_amount"] == "0.00"
    again = await client.post(f"{V1}/reminders/{rid}/payments", headers=h, json={})
    assert again.status_code == 409 and again.json()["code"] == "business_rule_violation"
    done = (await client.get(f"{V1}/reminders?status=completed", headers=h)).json()
    assert [d["id"] for d in done] == [rid]
    assert (await client.get(f"{V1}/reminders?status=active", headers=h)).json() == []


async def test_payment_body_optional_and_custom_amount(client):
    h = await _h(client)
    rid = (await client.post(f"{V1}/reminders/regular", headers=h, json=REG)).json()["id"]
    r = await client.post(f"{V1}/reminders/{rid}/payments", headers=h)          # no body at all
    assert r.status_code == 200 and r.json()["paid_amount"] == "500.00"
    r = await client.post(f"{V1}/reminders/{rid}/payments", headers=h, json={"amount": "123.45"})
    assert r.json()["paid_amount"] == "623.45"
    for bad in ({"amount": "0"}, {"amount": "-1"}, {"amount": "abc"}):
        assert (await client.post(f"{V1}/reminders/{rid}/payments", headers=h, json=bad)).status_code == 422


async def test_preview_does_not_save(client):
    h = await _h(client)
    body = {"total_amount": "1200", "interest_rate": "0", "months_total": 12, "payment_type": "annuity"}
    r = await client.post(f"{V1}/reminders/credit/preview", headers=h, json=body)
    p = r.json()
    assert r.status_code == 200 and p["first_payment"] == "100.00" and p["overpayment"] == "0.00"
    assert len(p["schedule"]) == 12 and p["schedule"][0]["principal_part"] == "100.00"
    assert (await client.get(f"{V1}/reminders", headers=h)).json() == []


@pytest.mark.parametrize("patch", [
    {"name": ""}, {"name": "x" * 129}, {"total_amount": "0"}, {"total_amount": "-5"},
    {"interest_rate": "-1"}, {"interest_rate": "100.01"}, {"months_total": 0}, {"months_total": 601},
    {"payment_type": "balloon"}, {"first_payment_date": "31.01.2026"}, {"total_amount": "12345678901234.5"},
])
async def test_credit_validation(client, patch):
    h = await _h(client)
    assert (await client.post(f"{V1}/reminders/credit", headers=h, json={**CREDIT, **patch})).status_code == 422
    # The preview endpoint validates the fields it shares with creation, and ignores the rest.
    preview_fields = {"total_amount", "interest_rate", "months_total", "payment_type"}
    body = {k: v for k, v in {**CREDIT, **patch}.items() if k in preview_fields}
    expected = 422 if set(patch) & preview_fields else 200
    assert (await client.post(f"{V1}/reminders/credit/preview", headers=h, json=body)).status_code == expected


@pytest.mark.parametrize("kind,body,missing", [
    ("installment", INSTALL, "monthly_payment"), ("education", EDU, "payment_amount"),
    ("regular", REG, "first_payment_date"), ("credit", CREDIT, "interest_rate"),
])
async def test_missing_required_field_is_422(client, kind, body, missing):
    h = await _h(client)
    r = await client.post(f"{V1}/reminders/{kind}", headers=h, json={k: v for k, v in body.items() if k != missing})
    assert r.status_code == 422 and r.json()["code"] == "validation_error"


async def test_isolation_and_delete(client):
    owner, other = await _h(client, 1), await _h(client, 2)
    rid = (await client.post(f"{V1}/reminders/regular", headers=owner, json=REG)).json()["id"]
    assert (await client.get(f"{V1}/reminders", headers=other)).json() == []
    for call in (client.get(f"{V1}/reminders/{rid}", headers=other),
                 client.post(f"{V1}/reminders/{rid}/payments", headers=other, json={}),
                 client.delete(f"{V1}/reminders/{rid}", headers=other)):
        assert (await call).status_code == 404
    assert (await client.delete(f"{V1}/reminders/{rid}", headers=owner)).status_code == 204
    assert (await client.get(f"{V1}/reminders/{rid}", headers=owner)).status_code == 404
