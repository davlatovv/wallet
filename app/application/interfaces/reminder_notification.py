from abc import ABC, abstractmethod
from datetime import date
from decimal import Decimal


class AbstractReminderNotificationService(ABC):

    @abstractmethod
    async def send_payment_reminder(
        self,
        user_id: int,
        reminder_name: str,
        amount: Decimal,
        next_date: date,
    ) -> None:
        ...
