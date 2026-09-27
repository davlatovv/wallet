from decimal import Decimal

import pytest

from app.domain.value_objects.money import Money


def test_negative_amount_rejected():
    with pytest.raises(ValueError):
        Money(Decimal("-1"))


def test_add_and_ratio():
    total = Money(Decimal("100")) + Money(Decimal("50"))
    assert total.amount == Decimal("150")
    assert Money(Decimal("50")).ratio(Money(Decimal("200"))) == Decimal("0.25")


def test_ratio_with_zero_denominator_is_zero():
    assert Money(Decimal("5")).ratio(Money(Decimal("0"))) == Decimal("0")


def test_format():
    assert Money(Decimal("1234.5")).format() == "1,234.50 UZS"
