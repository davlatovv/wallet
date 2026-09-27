from datetime import date, datetime
from decimal import Decimal

from pydantic import BaseModel, Field

from app.domain.entities.savings import SavingsGoalEntity, SavingsStatus
from app.presentation.api.schemas.common import MoneyStr


class CreateSavingsGoalRequest(BaseModel):
    name: str = Field(min_length=1, max_length=128)
    target_amount: Decimal = Field(gt=0, max_digits=15, decimal_places=2)
    description: str | None = Field(default=None, max_length=500)
    deadline: date | None = None


class DepositRequest(BaseModel):
    """Moves money from the card account into the goal (recorded as a savings transaction)."""

    amount: Decimal = Field(gt=0, max_digits=15, decimal_places=2)


class SavingsGoalResponse(BaseModel):
    id: int
    name: str
    target_amount: MoneyStr
    current_amount: MoneyStr
    remaining: MoneyStr
    progress_percent: int
    description: str | None
    deadline: date | None
    status: SavingsStatus
    created_at: datetime

    @classmethod
    def from_entity(cls, g: SavingsGoalEntity) -> "SavingsGoalResponse":
        return cls(id=g.id, name=g.name, target_amount=g.target_amount, current_amount=g.current_amount,
                   remaining=g.remaining, progress_percent=g.progress_percent,
                   description=g.description, deadline=g.deadline, status=g.status,
                   created_at=g.created_at)
