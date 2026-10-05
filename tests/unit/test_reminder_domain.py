from datetime import date

import pytest

from app.domain.entities.reminder import next_payment_date


@pytest.mark.parametrize("current,day,expected", [
    (date(2026, 1, 15), 15, date(2026, 2, 15)),
    (date(2026, 1, 31), 31, date(2026, 2, 28)),      # clamp to short month
    (date(2026, 2, 28), 31, date(2026, 3, 31)),      # ...and recover: no drift
    (date(2028, 1, 31), 31, date(2028, 2, 29)),      # leap year
    (date(2026, 12, 10), 10, date(2027, 1, 10)),     # year rollover
    (date(2026, 3, 31), 30, date(2026, 4, 30)),
    (date(2026, 1, 20), 5, date(2026, 2, 5)),        # anchored on payment_day, not on `current`
])
def test_next_payment_date(current, day, expected):
    assert next_payment_date(current, day) == expected


def test_no_drift_over_a_full_year():
    d, seen = date(2026, 1, 31), []
    for _ in range(12):
        d = next_payment_date(d, 31)
        seen.append(d.day)
    assert seen == [28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31, 31]
