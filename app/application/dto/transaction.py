from datetime import datetime, timezone
from decimal import Decimal

from pydantic import BaseModel, field_validator, model_validator

from app.domain.entities.transaction import AccountType


class AddTransactionDTO(BaseModel):
    user_id: int
    amount: Decimal
    category_id: int | None = None
    note: str | None = None
    currency: str = "UZS"
    account_type: AccountType | None = None
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

    @model_validator(mode="after")
    def account_type_from_currency(self) -> "AddTransactionDTO":
        if self.account_type is None:
            self.account_type = AccountType.from_currency(self.currency)
        return self


class UpdateTransactionDTO(BaseModel):
    """Partial update: only fields present in the payload are changed
    (so `category_id=None` explicitly clears the category).

    `amount` is the amount as entered, in the resulting currency (for USD: dollars);
    the UZS equivalent and rate are derived server-side.
    The transaction type cannot change; delete and re-create instead.
    """

    user_id: int
    transaction_id: int
    amount: Decimal | None = None
    category_id: int | None = None
    note: str | None = None
    currency: str | None = None
    account_type: AccountType | None = None
    created_at: datetime | None = None

    @field_validator("amount")
    @classmethod
    def amount_positive(cls, v: Decimal | None) -> Decimal | None:
        if v is None:
            return v
        return AddTransactionDTO.amount_positive(v)

    @field_validator("currency")
    @classmethod
    def currency_supported(cls, v: str | None) -> str | None:
        if v is None:
            return v
        return AddTransactionDTO.currency_supported(v)

    @field_validator("created_at")
    @classmethod
    def created_at_aware(cls, v: datetime | None) -> datetime | None:
        if v is not None and v.tzinfo is None:
            return v.replace(tzinfo=timezone.utc)  # naive input is interpreted as UTC
        return v
