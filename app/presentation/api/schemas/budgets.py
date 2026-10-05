from datetime import date
from decimal import Decimal

from pydantic import BaseModel, Field

from app.application.use_cases.budgets.manage_budgets import BudgetProgress
from app.domain.entities.budget import BudgetEntity, BudgetPeriod
from app.presentation.api.schemas.common import MoneyStr


class SetBudgetRequest(BaseModel):
    """Upsert keyed by (category_id, period). `category_id: null` = overall budget."""

    category_id: int | None = None
    period: BudgetPeriod
    limit_amount: Decimal = Field(gt=0, max_digits=15, decimal_places=2)


class BudgetResponse(BaseModel):
    id: int
    category_id: int | None
    category_name: str | None
    period: BudgetPeriod
    limit_amount: MoneyStr
    start_date: date

    @classmethod
    def from_entity(cls, b: BudgetEntity) -> "BudgetResponse":
        return cls(id=b.id, category_id=b.category_id, category_name=b.category_name,
                   period=b.period, limit_amount=b.limit_amount, start_date=b.start_date)


class BudgetProgressResponse(BudgetResponse):
    spent: MoneyStr
    used_ratio: float
    is_warning: bool
    is_critical: bool

    @classmethod
    def from_progress(cls, p: BudgetProgress) -> "BudgetProgressResponse":
        base = BudgetResponse.from_entity(p.budget)
        return cls(**base.model_dump(), spent=p.spent, used_ratio=round(float(p.ratio), 4),
                   is_warning=p.is_warning, is_critical=p.is_critical)
