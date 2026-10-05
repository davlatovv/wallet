from datetime import datetime, timezone as dt_timezone
from decimal import Decimal

from datetime import timedelta

from app.application.use_cases.analytics.get_report import (
    GetReportUseCase, ListReportMonthsUseCase, ReportPeriod, _period_range,
)
from tests.fakes import FakeTransactionRepo


def test_year_period_starts_jan_first():
    from_dt, to_dt = _period_range(ReportPeriod.YEAR)
    assert (from_dt.month, from_dt.day, from_dt.hour) == (1, 1, 0)
    assert from_dt.year == to_dt.year == datetime.now(dt_timezone.utc).year


def test_day_boundary_shifts_with_timezone():
    """The same instant can be "today" in one timezone and "yesterday" in another;
    the query range (in UTC) must reflect the requested timezone, not the server's."""
    utc_from, _ = _period_range(ReportPeriod.DAY, "UTC")
    tashkent_from, _ = _period_range(ReportPeriod.DAY, "Asia/Tashkent")  # UTC+5
    assert tashkent_from - utc_from == timedelta(hours=-5) or utc_from - tashkent_from == timedelta(hours=5)
    assert utc_from.tzinfo is not None and tashkent_from.tzinfo is not None


def test_unknown_timezone_falls_back_to_utc():
    from_dt, _ = _period_range(ReportPeriod.DAY, "Nowhere/Place")
    utc_from, _ = _period_range(ReportPeriod.DAY, "UTC")
    assert from_dt == utc_from


async def test_execute_accepts_timezone_and_defaults_to_utc():
    txs = FakeTransactionRepo()
    r1 = await GetReportUseCase(txs).execute(1, ReportPeriod.DAY)
    r2 = await GetReportUseCase(txs).execute(1, ReportPeriod.DAY, "Asia/Tashkent")
    assert r1.from_dt != r2.from_dt


async def test_report_and_months_delegate_to_repo():
    txs = FakeTransactionRepo()
    res = await GetReportUseCase(txs).execute(1, ReportPeriod.YEAR)
    assert res.period == ReportPeriod.YEAR and res.balance == 0

    async def months(user_id): return [(2026, 9), (2026, 8)]
    txs.list_available_months = months
    assert await ListReportMonthsUseCase(txs).execute(1) == [(2026, 9), (2026, 8)]
