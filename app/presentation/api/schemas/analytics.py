from datetime import datetime

from pydantic import BaseModel

from app.application.use_cases.analytics.get_report import ReportPeriod, ReportResult
from app.presentation.api.schemas.common import MoneyStr


class CategoryBreakdownResponse(BaseModel):
    category_id: int
    category_name: str
    amount: MoneyStr
    percent: float


class ReportResponse(BaseModel):
    period: ReportPeriod
    from_dt: datetime
    to_dt: datetime
    total_income: MoneyStr
    total_expense: MoneyStr
    total_savings: MoneyStr
    balance: MoneyStr
    expense_by_category: list[CategoryBreakdownResponse]
    income_by_category: list[CategoryBreakdownResponse]

    @classmethod
    def from_result(cls, r: ReportResult) -> "ReportResponse":
        def rows(items):
            return [CategoryBreakdownResponse(category_id=i.category_id, category_name=i.category_name,
                                              amount=i.amount, percent=i.percent) for i in items]
        return cls(period=r.period, from_dt=r.from_dt, to_dt=r.to_dt, total_income=r.total_income,
                   total_expense=r.total_expense, total_savings=r.total_savings, balance=r.balance,
                   expense_by_category=rows(r.expense_by_category),
                   income_by_category=rows(r.income_by_category))


class MonthResponse(BaseModel):
    year: int
    month: int
