from decimal import Decimal

import pytest
from pydantic import ValidationError

from app.application.dto.transaction import AddTransactionDTO
from app.domain.entities.transaction import AccountType


@pytest.mark.parametrize("currency,expected", [
    ("UZS", AccountType.CARD),
    ("USD", AccountType.CURRENCY),
    ("CASH", AccountType.CASH),
])
def test_account_type_derived_from_currency(currency, expected):
    dto = AddTransactionDTO(user_id=1, amount=Decimal("10"), currency=currency)
    assert dto.account_type == expected


def test_explicit_account_type_wins():
    dto = AddTransactionDTO(user_id=1, amount=Decimal("10"), account_type=AccountType.CASH)
    assert dto.account_type == AccountType.CASH


@pytest.mark.parametrize("amount", [Decimal("0"), Decimal("-5")])
def test_amount_must_be_positive(amount):
    with pytest.raises(ValidationError):
        AddTransactionDTO(user_id=1, amount=amount)


def test_unsupported_currency_rejected():
    with pytest.raises(ValidationError):
        AddTransactionDTO(user_id=1, amount=Decimal("1"), currency="EUR")


def test_amount_quantized_to_cents():
    assert AddTransactionDTO(user_id=1, amount=Decimal("1.239")).amount == Decimal("1.24")
