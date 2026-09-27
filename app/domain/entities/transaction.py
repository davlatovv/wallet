from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    SAVINGS = "savings"


class AccountType(str, Enum):
    CASH = "cash"
    CARD = "card"
    CURRENCY = "currency"

    @classmethod
    def from_currency(cls, currency: str | None) -> "AccountType":
        if currency == "CASH":
            return cls.CASH
        if currency == "USD":
            return cls.CURRENCY
        return cls.CARD


@dataclass
class TransactionEntity:
    id: int
    user_id: int
    amount: Decimal
    transaction_type: TransactionType
    category_id: int | None
    note: str | None
    created_at: datetime
    currency: str = "UZS"
    account_type: AccountType = AccountType.CARD
    original_amount: Decimal | None = None
    usd_rate: Decimal | None = None
    category_name: str | None = field(default=None)

    @property
    def signed_amount(self) -> Decimal:
        """Effect on the account balance: income adds, everything else subtracts."""
        return self.amount if self.transaction_type == TransactionType.INCOME else -self.amount
