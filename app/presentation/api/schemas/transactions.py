from datetime import datetime
from decimal import Decimal
from typing import Literal

from pydantic import BaseModel, Field

from app.domain.entities.transaction import AccountType, TransactionEntity, TransactionType
from app.presentation.api.schemas.common import MoneyStr

Currency = Literal["UZS", "USD", "CASH"]
_AMOUNT = dict(gt=0, max_digits=15, decimal_places=2)


class CreateTransactionRequest(BaseModel):
    """`amount` is what the user typed, in `currency` (dollars for USD).
    The server converts USD to UZS with the current CBU rate."""

    amount: Decimal = Field(**_AMOUNT)
    currency: Currency = "UZS"
    category_id: int | None = None
    note: str | None = Field(default=None, max_length=500)


class UpdateTransactionRequest(BaseModel):
    """Partial update: send only what changes. `category_id: null` clears the category.
    `amount` is in the resulting currency (required when switching to USD)."""

    amount: Decimal | None = Field(default=None, **_AMOUNT)
    currency: Currency | None = None
    category_id: int | None = None
    note: str | None = Field(default=None, max_length=500)
    created_at: datetime | None = None


class TransactionResponse(BaseModel):
    id: int
    transaction_type: TransactionType
    amount: MoneyStr  # UZS equivalent
    currency: str
    account_type: AccountType
    original_amount: MoneyStr | None
    usd_rate: MoneyStr | None
    category_id: int | None
    category_name: str | None
    note: str | None
    created_at: datetime

    @classmethod
    def from_entity(cls, e: TransactionEntity) -> "TransactionResponse":
        return cls(
            id=e.id, transaction_type=e.transaction_type, amount=e.amount, currency=e.currency,
            account_type=e.account_type, original_amount=e.original_amount, usd_rate=e.usd_rate,
            category_id=e.category_id, category_name=e.category_name, note=e.note,
            created_at=e.created_at,
        )


class BudgetAlertResponse(BaseModel):
    budget_id: int
    category_name: str | None
    used_ratio: float
    limit: str
    is_warning: bool
    is_critical: bool


class ExpenseCreatedResponse(BaseModel):
    transaction: TransactionResponse
    alerts: list[BudgetAlertResponse]


class TransactionListResponse(BaseModel):
    items: list[TransactionResponse]
    next_cursor: str | None


class UsdRateResponse(BaseModel):
    rate: MoneyStr
