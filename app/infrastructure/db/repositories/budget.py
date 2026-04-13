from datetime import date
from decimal import Decimal

from sqlalchemy import select, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.budget import BudgetEntity, BudgetPeriod
from app.domain.repositories.abstract_budget import AbstractBudgetRepository
from app.infrastructure.db.models.budget import Budget
from app.infrastructure.db.models.category import Category


def _to_entity(row: Budget, cat_name: str | None = None) -> BudgetEntity:
    return BudgetEntity(
        id=row.id,
        user_id=row.user_id,
        category_id=row.category_id,
        limit_amount=row.limit_amount,
        period=BudgetPeriod(row.period),
        start_date=row.start_date,
        category_name=cat_name,
    )


class SQLAlchemyBudgetRepository(AbstractBudgetRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id, category_id, limit_amount, period, start_date) -> BudgetEntity:
        b = Budget(
            user_id=user_id,
            category_id=category_id,
            limit_amount=limit_amount,
            period=period.value,
            start_date=start_date,
        )
        self._session.add(b)
        await self._session.flush()
        return _to_entity(b)

    async def get_by_id(self, budget_id: int, user_id: int) -> BudgetEntity | None:
        result = await self._session.execute(
            select(Budget, Category.name.label("cat_name"))
            .outerjoin(Category, Budget.category_id == Category.id)
            .where(Budget.id == budget_id, Budget.user_id == user_id)
        )
        row = result.one_or_none()
        return _to_entity(row.Budget, row.cat_name) if row else None

    async def list_by_user(self, user_id: int) -> list[BudgetEntity]:
        rows = (
            await self._session.execute(
                select(Budget, Category.name.label("cat_name"))
                .outerjoin(Category, Budget.category_id == Category.id)
                .where(Budget.user_id == user_id)
            )
        ).all()
        return [_to_entity(r.Budget, r.cat_name) for r in rows]

    async def delete(self, budget_id: int, user_id: int) -> bool:
        result = await self._session.execute(
            delete(Budget).where(Budget.id == budget_id, Budget.user_id == user_id)
        )
        return result.rowcount > 0
