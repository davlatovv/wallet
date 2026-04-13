from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
from enum import Enum


class DebtType(str, Enum):
    I_OWE = "i_owe"          # я должен
    OWED_TO_ME = "owed_to_me"  # мне должны


class DebtStatus(str, Enum):
    ACTIVE = "active"
    SETTLED = "settled"
    OVERDUE = "overdue"


@dataclass
class DebtEntity:
    id: int
    user_id: int
    counterparty: str
    amount: Decimal
    debt_type: DebtType
    status: DebtStatus
    description: str | None
    due_date: date | None
    created_at: datetime
