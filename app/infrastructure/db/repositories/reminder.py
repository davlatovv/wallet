from datetime import date
from decimal import Decimal

from dateutil.relativedelta import relativedelta
from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.reminder import (
    ReminderEntity,
    ReminderType,
    PaymentType,
    ReminderStatus,
)
from app.domain.repositories.abstract_reminder import AbstractReminderRepository
from app.infrastructure.db.models.reminder import Reminder


def _to_entity(row: Reminder) -> ReminderEntity:
    return ReminderEntity(
        id=row.id,
        user_id=row.user_id,
        reminder_type=ReminderType(row.reminder_type),
        name=row.name,
        payment_amount=row.payment_amount,
        payment_day=row.payment_day,
        next_payment_date=row.next_payment_date,
        total_amount=row.total_amount,
        paid_amount=row.paid_amount,
        months_total=row.months_total,
        months_paid=row.months_paid,
        interest_rate=row.interest_rate,
        payment_type=PaymentType(row.payment_type) if row.payment_type else None,
        status=ReminderStatus(row.status),
        reminder_enabled=row.reminder_enabled,
        created_at=row.created_at,
    )


class SQLAlchemyReminderRepository(AbstractReminderRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: int,
        reminder_type: ReminderType,
        name: str,
        payment_amount: Decimal,
        payment_day: int,
        next_payment_date: date,
        total_amount: Decimal | None,
        months_total: int | None,
        interest_rate: Decimal | None,
        payment_type: PaymentType | None,
    ) -> ReminderEntity:
        row = Reminder(
            user_id=user_id,
            reminder_type=reminder_type.value,
            name=name,
            payment_amount=payment_amount,
            payment_day=payment_day,
            next_payment_date=next_payment_date,
            total_amount=total_amount,
            paid_amount=Decimal("0"),
            months_total=months_total,
            months_paid=0,
            interest_rate=interest_rate,
            payment_type=payment_type.value if payment_type else None,
            status=ReminderStatus.ACTIVE.value,
            reminder_enabled=True,
        )
        self._session.add(row)
        await self._session.flush()
        return _to_entity(row)

    async def get_by_id(self, reminder_id: int, user_id: int) -> ReminderEntity | None:
        result = await self._session.execute(
            select(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        return _to_entity(row) if row else None

    async def list_by_user(self, user_id: int) -> list[ReminderEntity]:
        rows = (
            await self._session.execute(
                select(Reminder)
                .where(Reminder.user_id == user_id)
                .order_by(Reminder.next_payment_date.asc())
            )
        ).scalars().all()
        return [_to_entity(r) for r in rows]

    async def list_due_today(self, today: date) -> list[ReminderEntity]:
        rows = (
            await self._session.execute(
                select(Reminder).where(
                    Reminder.next_payment_date == today,
                    Reminder.status == ReminderStatus.ACTIVE.value,
                    Reminder.reminder_enabled.is_(True),
                )
            )
        ).scalars().all()
        return [_to_entity(r) for r in rows]

    async def record_payment(self, reminder_id: int, user_id: int, amount: Decimal) -> ReminderEntity | None:
        entity = await self.get_by_id(reminder_id, user_id)
        if not entity or entity.status != ReminderStatus.ACTIVE:
            return None

        new_paid = entity.paid_amount + amount
        new_months_paid = entity.months_paid + 1

        # Determine completion
        completed = False
        if entity.months_total is not None and new_months_paid >= entity.months_total:
            completed = True
        elif entity.total_amount is not None and new_paid >= entity.total_amount:
            completed = True

        new_status = ReminderStatus.COMPLETED.value if completed else ReminderStatus.ACTIVE.value

        # Advance next payment date by 1 month (only if still active)
        new_next_date = entity.next_payment_date
        if not completed:
            new_next_date = entity.next_payment_date + relativedelta(months=1)

        await self._session.execute(
            update(Reminder)
            .where(Reminder.id == reminder_id, Reminder.user_id == user_id)
            .values(
                paid_amount=new_paid,
                months_paid=new_months_paid,
                next_payment_date=new_next_date,
                status=new_status,
            )
        )
        return await self.get_by_id(reminder_id, user_id)

    async def delete(self, reminder_id: int, user_id: int) -> bool:
        result = await self._session.execute(
            delete(Reminder).where(Reminder.id == reminder_id, Reminder.user_id == user_id)
        )
        return result.rowcount > 0
