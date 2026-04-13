from abc import ABC, abstractmethod

from app.domain.entities.transaction import TransactionEntity


class AbstractUserRepository(ABC):
    @abstractmethod
    async def get_or_create(self, telegram_id: int, username: str | None, first_name: str | None) -> bool:
        """Returns True if user was created, False if already existed."""

    @abstractmethod
    async def exists(self, telegram_id: int) -> bool:
        ...
