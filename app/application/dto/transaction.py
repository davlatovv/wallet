from decimal import Decimal
from pydantic import BaseModel, field_validator


class AddTransactionDTO(BaseModel):
    user_id: int
    amount: Decimal
    category_id: int | None = None
    note: str | None = None
    currency: str = "UZS"
    original_amount: Decimal | None = None
    usd_rate: Decimal | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal) -> Decimal:
        if v <= Decimal("0"):
            raise ValueError("Amount must be positive")
        return v.quantize(Decimal("0.01"))

    @field_validator("currency")
    @classmethod
    def currency_supported(cls, v: str) -> str:
        if v not in {"UZS", "USD", "CASH"}:
            raise ValueError("Unsupported currency")
        return v
