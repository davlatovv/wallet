from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.entities.debt import DebtEntity, DebtStatus, DebtType
from app.presentation.api.schemas.common import MoneyStr


class CreateDebtRequest(BaseModel):
    counterparty: str = Field(min_length=1, max_length=128)
    amount: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    debt_type: DebtType
    description: str | None = Field(default=None, max_length=500)
    due_date: date | None = None


class DebtResponse(BaseModel):
    id: int
    counterparty: str
    amount: MoneyStr
    debt_type: DebtType
    status: DebtStatus
    description: str | None
    due_date: date | None
    created_at: datetime

    @classmethod
    def from_entity(cls, d: DebtEntity) -> "DebtResponse":
        return cls(id=d.id, counterparty=d.counterparty, amount=d.amount, debt_type=d.debt_type,
                   status=d.status, description=d.description, due_date=d.due_date,
                   created_at=d.created_at)
