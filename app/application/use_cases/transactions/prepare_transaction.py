from decimal import ROUND_HALF_UP, Decimal

from app.application.dto.transaction import AddTransactionDTO
from app.application.interfaces.currency_rate import AbstractUsdRateProvider
from app.domain.exceptions.base import NotFoundError
from app.domain.repositories.abstract_category import AbstractCategoryRepository


def usd_to_uzs(usd_amount: Decimal, rate: Decimal) -> Decimal:
    return (usd_amount * rate).quantize(Decimal("1"), rounding=ROUND_HALF_UP)


class PrepareTransactionUseCase:
    """Turns user input (amount as entered + currency) into a storable DTO:
    verifies the category belongs to the user and, for USD, fetches the rate and
    computes the UZS equivalent. Shared by the income and expense flows."""

    def __init__(
        self,
        category_repo: AbstractCategoryRepository,
        rate_provider: AbstractUsdRateProvider,
    ) -> None:
        self._cat_repo = category_repo
        self._rates = rate_provider

    async def execute(
        self,
        user_id: int,
        amount: Decimal,
        currency: str = "UZS",
        category_id: int | None = None,
        note: str | None = None,
    ) -> AddTransactionDTO:
        if category_id is not None and await self._cat_repo.get_by_id(category_id, user_id) is None:
            raise NotFoundError(f"Category {category_id} not found")

        if currency == "USD":
            amount = amount.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
            rate = await self._rates.get_usd_rate()
            return AddTransactionDTO(
                user_id=user_id, amount=usd_to_uzs(amount, rate), currency="USD",
                category_id=category_id, note=note, original_amount=amount, usd_rate=rate,
            )
        return AddTransactionDTO(
            user_id=user_id, amount=amount, currency=currency,
            category_id=category_id, note=note,
        )
