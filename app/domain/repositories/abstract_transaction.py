from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal

from app.domain.entities.transaction import TransactionEntity, TransactionType


class AbstractTransactionRepository(ABC):
    @abstractmethod
    async def create(
        self,
        user_id: int,
        amount: Decimal,
        transaction_type: TransactionType,
        category_id: int | None,
        note: str | None,
    ) -> TransactionEntity:
        ...

    @abstractmethod
    async def get_by_id(self, transaction_id: int, user_id: int) -> TransactionEntity | None:
        ...

    @abstractmethod
    async def list_by_period(
        self,
        user_id: int,
        from_dt: datetime,
        to_dt: datetime,
        transaction_type: TransactionType | None = None,
    ) -> list[TransactionEntity]:
        ...

    @abstractmethod
    async def list_available_months(self, user_id: int) -> list[tuple[int, int]]:
        """Returns available transaction months as (year, month), newest first."""
        ...

    @abstractmethod
    async def delete(self, transaction_id: int, user_id: int) -> bool:
        ...

    @abstractmethod
    async def sum_by_period(
        self,
        user_id: int,
        from_dt: datetime,
        to_dt: datetime,
        transaction_type: TransactionType,
    ) -> Decimal:
        ...

    @abstractmethod
    async def sum_by_category(
        self,
        user_id: int,
        from_dt: datetime,
        to_dt: datetime,
        transaction_type: TransactionType,
    ) -> list[tuple[int, str, Decimal]]:
        """Returns list of (category_id, category_name, total_amount)."""
        ...
