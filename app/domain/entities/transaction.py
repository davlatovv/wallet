from dataclasses import dataclass, field
from datetime import datetime
from decimal import Decimal
from enum import Enum


class TransactionType(str, Enum):
    INCOME = "income"
    EXPENSE = "expense"
    SAVINGS = "savings"


@dataclass
class TransactionEntity:
    id: int
    user_id: int
    amount: Decimal
    transaction_type: TransactionType
    category_id: int | None
    note: str | None
    created_at: datetime
    category_name: str | None = field(default=None)
