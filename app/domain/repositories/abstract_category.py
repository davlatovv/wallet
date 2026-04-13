from abc import ABC, abstractmethod

from app.domain.entities.category import CategoryEntity


class AbstractCategoryRepository(ABC):
    @abstractmethod
    async def create(
        self,
        user_id: int,
        name: str,
        icon: str | None,
        parent_id: int | None,
        category_type: str,
    ) -> CategoryEntity:
        ...

    @abstractmethod
    async def get_by_id(self, category_id: int, user_id: int) -> CategoryEntity | None:
        ...

    @abstractmethod
    async def list_by_user(self, user_id: int, category_type: str | None = None) -> list[CategoryEntity]:
        ...

    @abstractmethod
    async def list_root(self, user_id: int, category_type: str | None = None) -> list[CategoryEntity]:
        """Return only top-level categories (parent_id is None)."""
        ...

    @abstractmethod
    async def list_children(self, user_id: int, parent_id: int) -> list[CategoryEntity]:
        ...

    @abstractmethod
    async def update(self, category_id: int, user_id: int, name: str, icon: str | None) -> CategoryEntity | None:
        ...

    @abstractmethod
    async def delete(self, category_id: int, user_id: int) -> bool:
        ...

    @abstractmethod
    async def seed_defaults(self, user_id: int) -> None:
        """Create default system categories for a new user."""
        ...
