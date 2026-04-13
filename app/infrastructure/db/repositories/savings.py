from datetime import date
from decimal import Decimal

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.savings import SavingsGoalEntity, SavingsStatus
from app.domain.repositories.abstract_savings import AbstractSavingsRepository
from app.infrastructure.db.models.savings import SavingsGoal


def _to_entity(row: SavingsGoal) -> SavingsGoalEntity:
    return SavingsGoalEntity(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        target_amount=row.target_amount,
        current_amount=row.current_amount,
        description=row.description,
        deadline=row.deadline,
        status=SavingsStatus(row.status),
        created_at=row.created_at,
    )


class SQLAlchemySavingsRepository(AbstractSavingsRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id, name, target_amount, description, deadline) -> SavingsGoalEntity:
        g = SavingsGoal(
            user_id=user_id,
            name=name,
            target_amount=target_amount,
            description=description,
            deadline=deadline,
        )
        self._session.add(g)
        await self._session.flush()
        return _to_entity(g)

    async def get_by_id(self, goal_id: int, user_id: int) -> SavingsGoalEntity | None:
        result = await self._session.execute(
            select(SavingsGoal).where(SavingsGoal.id == goal_id, SavingsGoal.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        return _to_entity(row) if row else None

    async def list_by_user(self, user_id: int, status: SavingsStatus | None = None) -> list[SavingsGoalEntity]:
        stmt = select(SavingsGoal).where(SavingsGoal.user_id == user_id).order_by(SavingsGoal.created_at.desc())
        if status:
            stmt = stmt.where(SavingsGoal.status == status.value)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(r) for r in rows]

    async def add_funds(self, goal_id: int, user_id: int, amount: Decimal) -> SavingsGoalEntity | None:
        goal = await self.get_by_id(goal_id, user_id)
        if not goal:
            return None
        new_amount = goal.current_amount + amount
        new_status = SavingsStatus.COMPLETED.value if new_amount >= goal.target_amount else goal.status.value
        await self._session.execute(
            update(SavingsGoal)
            .where(SavingsGoal.id == goal_id, SavingsGoal.user_id == user_id)
            .values(current_amount=new_amount, status=new_status)
        )
        return await self.get_by_id(goal_id, user_id)

    async def mark_completed(self, goal_id: int, user_id: int) -> SavingsGoalEntity | None:
        await self._session.execute(
            update(SavingsGoal)
            .where(SavingsGoal.id == goal_id, SavingsGoal.user_id == user_id)
            .values(status=SavingsStatus.COMPLETED.value)
        )
        return await self.get_by_id(goal_id, user_id)

    async def delete(self, goal_id: int, user_id: int) -> bool:
        result = await self._session.execute(
            delete(SavingsGoal).where(SavingsGoal.id == goal_id, SavingsGoal.user_id == user_id)
        )
        return result.rowcount > 0
