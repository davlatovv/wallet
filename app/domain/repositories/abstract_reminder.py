from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal

from app.domain.entities.reminder import ReminderEntity, ReminderType, PaymentType


class AbstractReminderRepository(ABC):

    @abstractmethod
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
        ...

    @abstractmethod
    async def get_by_id(self, reminder_id: int, user_id: int) -> ReminderEntity | None:
        ...

    @abstractmethod
    async def list_by_user(self, user_id: int) -> list[ReminderEntity]:
        ...

    @abstractmethod
    async def list_due_today(self, today: date) -> list[ReminderEntity]:
        """All active reminders whose next_payment_date == today."""
        ...

    @abstractmethod
    async def record_payment(self, reminder_id: int, user_id: int, amount: Decimal) -> ReminderEntity | None:
        """
        Add amount to paid_amount, increment months_paid,
        advance next_payment_date by 1 month, mark completed if done.
        """
        ...

    @abstractmethod
    async def delete(self, reminder_id: int, user_id: int) -> bool:
        ...
