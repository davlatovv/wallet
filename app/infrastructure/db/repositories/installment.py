from datetime import date
from decimal import Decimal
from dateutil.relativedelta import relativedelta

from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.installment import InstallmentEntity, InstallmentStatus
from app.domain.repositories.abstract_installment import AbstractInstallmentRepository
from app.infrastructure.db.models.installment import Installment


def _to_entity(row: Installment) -> InstallmentEntity:
    return InstallmentEntity(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        total_amount=row.total_amount,
        monthly_payment=row.monthly_payment,
        months_total=row.months_total,
        months_paid=row.months_paid,
        next_payment_date=row.next_payment_date,
        description=row.description,
        status=InstallmentStatus(row.status),
        created_at=row.created_at,
    )


class SQLAlchemyInstallmentRepository(AbstractInstallmentRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id, name, total_amount, monthly_payment, months_total, next_payment_date, description) -> InstallmentEntity:
        inst = Installment(
            user_id=user_id,
            name=name,
            total_amount=total_amount,
            monthly_payment=monthly_payment,
            months_total=months_total,
            months_paid=0,
            next_payment_date=next_payment_date,
            description=description,
            status=InstallmentStatus.ACTIVE.value,
        )
        self._session.add(inst)
        await self._session.flush()
        return _to_entity(inst)

    async def get_by_id(self, installment_id: int, user_id: int) -> InstallmentEntity | None:
        result = await self._session.execute(
            select(Installment).where(Installment.id == installment_id, Installment.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        return _to_entity(row) if row else None

    async def list_by_user(self, user_id: int) -> list[InstallmentEntity]:
        rows = (
            await self._session.execute(
                select(Installment).where(Installment.user_id == user_id).order_by(Installment.created_at.desc())
            )
        ).scalars().all()
        return [_to_entity(r) for r in rows]

    async def pay_month(self, installment_id: int, user_id: int) -> InstallmentEntity | None:
        inst = await self.get_by_id(installment_id, user_id)
        if not inst or inst.status != InstallmentStatus.ACTIVE:
            return None
        new_paid = inst.months_paid + 1
        new_status = InstallmentStatus.COMPLETED.value if new_paid >= inst.months_total else InstallmentStatus.ACTIVE.value
        new_next = None
        if inst.next_payment_date and new_status == InstallmentStatus.ACTIVE.value:
            new_next = inst.next_payment_date + relativedelta(months=1)
        await self._session.execute(
            update(Installment)
            .where(Installment.id == installment_id, Installment.user_id == user_id)
            .values(months_paid=new_paid, status=new_status, next_payment_date=new_next)
        )
        return await self.get_by_id(installment_id, user_id)

    async def delete(self, installment_id: int, user_id: int) -> bool:
        result = await self._session.execute(
            delete(Installment).where(Installment.id == installment_id, Installment.user_id == user_id)
        )
        return result.rowcount > 0
