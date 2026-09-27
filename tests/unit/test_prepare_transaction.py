from decimal import Decimal

import pytest

from app.application.use_cases.transactions.prepare_transaction import PrepareTransactionUseCase
from app.domain.entities.transaction import AccountType
from app.domain.exceptions.base import ExternalServiceError, NotFoundError
from tests.fakes import FakeCategoryRepo, FakeRateProvider

D = Decimal


def _uc(rate="12500", fail=False):
    rates = FakeRateProvider(rate, fail)
    return PrepareTransactionUseCase(FakeCategoryRepo({5: 1, 6: 2}), rates), rates


async def test_uzs_passthrough_does_not_hit_rate_api():
    uc, rates = _uc()
    dto = await uc.execute(1, D("1000"), "UZS", 5, "n")
    assert (dto.amount, dto.currency, dto.original_amount, dto.usd_rate) == (D("1000"), "UZS", None, None)
    assert dto.account_type == AccountType.CARD and rates.calls == 0


async def test_usd_is_converted_server_side_and_rounded():
    uc, _ = _uc("12345.67")
    dto = await uc.execute(1, D("10.50"), "USD")
    assert dto.original_amount == D("10.50") and dto.usd_rate == D("12345.67")
    assert dto.amount == D("129630")  # 10.50 * 12345.67 = 129629.535, UZS stored as whole sums
    assert dto.account_type == AccountType.CURRENCY


async def test_cash_currency_maps_to_cash_account():
    uc, _ = _uc()
    assert (await uc.execute(1, D("5"), "CASH")).account_type == AccountType.CASH


async def test_foreign_or_missing_category_rejected():
    uc, _ = _uc()
    for bad in (6, 999):
        with pytest.raises(NotFoundError):
            await uc.execute(1, D("1"), "UZS", bad)


async def test_rate_outage_propagates():
    uc, _ = _uc(fail=True)
    with pytest.raises(ExternalServiceError):
        await uc.execute(1, D("1"), "USD")
