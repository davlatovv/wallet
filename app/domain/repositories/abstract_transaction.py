from abc import ABC, abstractmethod
from datetime import datetime
from decimal import Decimal
from typing import Any

from app.domain.entities.transaction import AccountType, TransactionEntity, TransactionType


class AbstractTransactionRepository(ABC):
    @abstractmethod
    async def create(
        self,
        user_id: int,
        amount: Decimal,
        transaction_type: TransactionType,
        category_id: int | None,
        note: str | None,
        currency: str = "UZS",
        account_type: AccountType = AccountType.CARD,
        original_amount: Decimal | None = None,
        usd_rate: Decimal | None = None,
    ) -> TransactionEntity:
        ...

    @abstractmethod
    async def get_by_id(
        self, transaction_id: int, user_id: int, for_update: bool = False
    ) -> TransactionEntity | None:
        """`for_update` locks the row until the surrounding DB transaction ends."""
        ...

    @abstractmethod
    async def list_page(
        self,
        user_id: int,
        limit: int,
        transaction_type: TransactionType | None = None,
        category_id: int | None = None,
        from_dt: datetime | None = None,
        to_dt: datetime | None = None,
        before: tuple[datetime, int] | None = None,
    ) -> list[TransactionEntity]:
        """Newest first (created_at, id). `before` is the (created_at, id) of the last
        row of the previous page; only strictly older rows are returned."""
        ...

    @abstractmethod
    async def update(
        self, transaction_id: int, user_id: int, changes: dict[str, Any]
    ) -> TransactionEntity | None:
        """Applies column changes (keys are TransactionEntity field names)."""
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
        category_id: int | None = None,
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

    @abstractmethod
    async def sum_balance_by_currency(
        self,
        user_id: int,
        from_dt: datetime,
        to_dt: datetime,
    ) -> list[tuple[str, Decimal]]:
        """Returns net balance grouped by currency/account type."""
        ...
