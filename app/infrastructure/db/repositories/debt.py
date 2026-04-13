from datetime import date
from decimal import Decimal

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.debt import DebtEntity, DebtType, DebtStatus
from app.domain.repositories.abstract_debt import AbstractDebtRepository
from app.infrastructure.db.models.debt import Debt


def _to_entity(row: Debt) -> DebtEntity:
    return DebtEntity(
        id=row.id,
        user_id=row.user_id,
        counterparty=row.counterparty,
        amount=row.amount,
        debt_type=DebtType(row.debt_type),
        status=DebtStatus(row.status),
        description=row.description,
        due_date=row.due_date,
        created_at=row.created_at,
    )


class SQLAlchemyDebtRepository(AbstractDebtRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id, counterparty, amount, debt_type, description, due_date) -> DebtEntity:
        d = Debt(
            user_id=user_id,
            counterparty=counterparty,
            amount=amount,
            debt_type=debt_type.value,
            description=description,
            due_date=due_date,
            status=DebtStatus.ACTIVE.value,
        )
        self._session.add(d)
        await self._session.flush()
        return _to_entity(d)

    async def get_by_id(self, debt_id: int, user_id: int) -> DebtEntity | None:
        result = await self._session.execute(
            select(Debt).where(Debt.id == debt_id, Debt.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        return _to_entity(row) if row else None

    async def list_by_user(self, user_id: int, status: DebtStatus | None = None) -> list[DebtEntity]:
        stmt = select(Debt).where(Debt.user_id == user_id).order_by(Debt.created_at.desc())
        if status:
            stmt = stmt.where(Debt.status == status.value)
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(r) for r in rows]

    async def settle(self, debt_id: int, user_id: int) -> DebtEntity | None:
        await self._session.execute(
            update(Debt)
            .where(Debt.id == debt_id, Debt.user_id == user_id)
            .values(status=DebtStatus.SETTLED.value)
        )
        return await self.get_by_id(debt_id, user_id)

    async def delete(self, debt_id: int, user_id: int) -> bool:
        result = await self._session.execute(
            delete(Debt).where(Debt.id == debt_id, Debt.user_id == user_id)
        )
        return result.rowcount > 0
