"""Reminder use cases running on the real repository (SQLite)."""
from datetime import date
from decimal import Decimal

import pytest

from app.application.dto.reminder import (
    CreateCreditReminderDTO, CreateInstallmentReminderDTO, CreateRegularReminderDTO,
)
from app.application.use_cases.reminders.manage_reminders import (
    CreateCreditReminderUseCase, CreateInstallmentReminderUseCase, CreateRegularReminderUseCase,
    DeleteReminderUseCase, GetReminderDetailUseCase, PreviewCreditUseCase, RecordPaymentUseCase,
)
from app.domain.entities.reminder import PaymentType, ReminderStatus
from app.domain.exceptions.base import BusinessRuleViolation, NotFoundError, ValidationError
from app.infrastructure.db.repositories.reminder import SQLAlchemyReminderRepository

D = Decimal


@pytest.fixture
def repo(session):
    return SQLAlchemyReminderRepository(session)


def _credit(months=3, ptype=PaymentType.DIFFERENTIAL, rate="12", total="3000", first=date(2026, 1, 31)):
    return CreateCreditReminderDTO(
        name="Car", total_amount=D(total), interest_rate=D(rate), months_total=months,
        payment_type=ptype, payment_day=first.day, first_payment_date=first)


async def test_differential_credit_payment_follows_the_schedule(repo):
    made = await CreateCreditReminderUseCase(repo).execute(1, _credit())
    sched = (await GetReminderDetailUseCase(repo).execute(made.id, 1)).payment_schedule
    payments = [r["payment"] for r in sched]
    assert payments[0] > payments[1] > payments[2]        # differential: declining
    assert made.payment_amount == payments[0]

    rec = RecordPaymentUseCase(repo)
    r1 = await rec.execute(made.id, 1)
    assert r1.paid_amount == payments[0]
    assert r1.payment_amount == payments[1]                # "next due" now reflects month 2
    assert r1.next_payment_date == date(2026, 2, 28)       # clamped
    r2 = await rec.execute(made.id, 1)
    assert r2.paid_amount == payments[0] + payments[1]     # recorded month-2 amount, not month-1 again
    assert r2.next_payment_date == date(2026, 3, 31)       # no drift back to the 28th


async def test_credit_completes_by_months_not_by_principal_reached(repo):
    """Regression: paid_amount passes the principal before the last month because payments
    include interest; the credit used to be marked completed at that point."""
    made = await CreateCreditReminderUseCase(repo).execute(
        1, _credit(months=12, ptype=PaymentType.ANNUITY, rate="100", total="1000"))
    rec = RecordPaymentUseCase(repo)
    results = [await rec.execute(made.id, 1) for _ in range(12)]
    still_active_past_principal = [
        r for r in results[:-1] if r.status == ReminderStatus.ACTIVE and r.paid_amount > D("1000")]
    assert still_active_past_principal, "scenario must pass the principal before the final month"
    assert [r.status for r in results[:-1]] == [ReminderStatus.ACTIVE] * 11
    assert results[-1].status == ReminderStatus.COMPLETED and results[-1].months_paid == 12


async def test_recording_on_completed_reminder_is_a_business_error(repo):
    made = await CreateInstallmentReminderUseCase(repo).execute(1, CreateInstallmentReminderDTO(
        name="Phone", total_amount=D("200"), monthly_payment=D("100"), months_total=2,
        payment_day=5, first_payment_date=date(2026, 1, 5)))
    rec = RecordPaymentUseCase(repo)
    await rec.execute(made.id, 1)
    last = await rec.execute(made.id, 1)
    assert last.status == ReminderStatus.COMPLETED and last.remaining_amount == D("0")
    with pytest.raises(BusinessRuleViolation):
        await rec.execute(made.id, 1)


async def test_custom_amount_and_validation(repo):
    made = await CreateRegularReminderUseCase(repo).execute(1, CreateRegularReminderDTO(
        name="Rent", payment_amount=D("500"), payment_day=1, first_payment_date=date(2026, 1, 1)))
    rec = RecordPaymentUseCase(repo)
    r = await rec.execute(made.id, 1, D("450"))
    assert (r.paid_amount, r.months_paid, r.status) == (D("450"), 1, ReminderStatus.ACTIVE)
    assert r.payment_amount == D("500")                    # regular payments keep their amount
    for bad in (D("0"), D("-5")):
        with pytest.raises(ValidationError):
            await rec.execute(made.id, 1, bad)


async def test_regular_never_completes(repo):
    made = await CreateRegularReminderUseCase(repo).execute(1, CreateRegularReminderDTO(
        name="Gym", payment_amount=D("10"), payment_day=15, first_payment_date=date(2026, 1, 15)))
    rec = RecordPaymentUseCase(repo)
    for _ in range(5):
        r = await rec.execute(made.id, 1)
    assert r.status == ReminderStatus.ACTIVE and r.months_paid == 5
    assert r.next_payment_date == date(2026, 6, 15)


async def test_other_users_reminder_is_not_found(repo):
    made = await CreateRegularReminderUseCase(repo).execute(1, CreateRegularReminderDTO(
        name="x", payment_amount=D("1"), payment_day=1, first_payment_date=date(2026, 1, 1)))
    with pytest.raises(NotFoundError):
        await RecordPaymentUseCase(repo).execute(made.id, 2)
    with pytest.raises(NotFoundError):
        await GetReminderDetailUseCase(repo).execute(made.id, 2)
    with pytest.raises(NotFoundError):
        await DeleteReminderUseCase(repo).execute(made.id, 2)
    assert (await GetReminderDetailUseCase(repo).execute(made.id, 1)).months_paid == 0


async def test_name_is_trimmed_and_validated(repo):
    uc = CreateRegularReminderUseCase(repo)
    ok = await uc.execute(1, CreateRegularReminderDTO(
        name="  Rent  ", payment_amount=D("1"), payment_day=1, first_payment_date=date(2026, 1, 1)))
    assert ok.name == "Rent"
    for bad in ("", "   ", "x" * 129):
        with pytest.raises(ValidationError):
            await uc.execute(1, CreateRegularReminderDTO(
                name=bad, payment_amount=D("1"), payment_day=1, first_payment_date=date(2026, 1, 1)))


def test_preview_annuity_and_differential():
    uc = PreviewCreditUseCase()
    ann = uc.execute(D("1200"), D("0"), 12, PaymentType.ANNUITY)
    assert ann.first_payment == D("100.00") and ann.overpayment == D("0.00") and len(ann.schedule) == 12
    diff = uc.execute(D("1200"), D("24"), 12, PaymentType.DIFFERENTIAL)
    assert diff.first_payment > diff.schedule[-1]["payment"]
    assert diff.total_payment - D("1200") == diff.overpayment > 0
    assert diff.schedule[-1]["balance"] == D("0")


@pytest.mark.parametrize("args", [
    (D("0"), D("10"), 12), (D("100"), D("-1"), 12), (D("100"), D("101"), 12),
    (D("100"), D("10"), 0), (D("100"), D("10"), 601),
])
def test_preview_validation(args):
    with pytest.raises(ValidationError):
        PreviewCreditUseCase().execute(*args, PaymentType.ANNUITY)
