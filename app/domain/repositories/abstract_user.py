from abc import ABC, abstractmethod
from decimal import Decimal

from app.domain.entities.transaction import AccountType
from app.domain.entities.user import UserBalanceEntity


class AbstractUserRepository(ABC):
    @abstractmethod
    async def get_or_create(self, telegram_id: int, username: str | None, first_name: str | None) -> bool:
        """Returns True if user was created, False if already existed."""

    @abstractmethod
    async def exists(self, telegram_id: int) -> bool:
        ...

    @abstractmethod
    async def get_timezone(self, user_id: int) -> str | None:
        ...

    @abstractmethod
    async def update_timezone(self, user_id: int, timezone: str) -> str | None:
        ...

    @abstractmethod
    async def get_balance(self, user_id: int) -> UserBalanceEntity | None:
        ...

    @abstractmethod
    async def apply_balance_delta(
        self,
        user_id: int,
        account_type: AccountType,
        amount_delta: Decimal,
    ) -> UserBalanceEntity | None:
        ...
