import logging

from app.domain.entities.category import CategoryEntity
from app.domain.exceptions.base import NotFoundError
from app.domain.repositories.abstract_category import AbstractCategoryRepository
from app.domain.repositories.abstract_user import AbstractUserRepository

logger = logging.getLogger(__name__)


class EnsureUserExistsUseCase:
    def __init__(self, user_repo: AbstractUserRepository, category_repo: AbstractCategoryRepository) -> None:
        self._user_repo = user_repo
        self._category_repo = category_repo

    async def execute(self, telegram_id: int, username: str | None, first_name: str | None) -> bool:
        created = await self._user_repo.get_or_create(telegram_id, username, first_name)
        if created:
            await self._category_repo.seed_defaults(telegram_id)
            logger.info("New user registered: %d, default categories seeded", telegram_id)
        return created


class ListCategoriesUseCase:
    def __init__(self, repo: AbstractCategoryRepository) -> None:
        self._repo = repo

    async def execute(self, user_id: int, category_type: str | None = None) -> list[CategoryEntity]:
        return await self._repo.list_root(user_id, category_type)


class CreateCategoryUseCase:
    def __init__(self, repo: AbstractCategoryRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        user_id: int,
        name: str,
        icon: str | None = None,
        parent_id: int | None = None,
        category_type: str = "expense",
    ) -> CategoryEntity:
        return await self._repo.create(user_id, name, icon, parent_id, category_type)


class DeleteCategoryUseCase:
    def __init__(self, repo: AbstractCategoryRepository) -> None:
        self._repo = repo

    async def execute(self, category_id: int, user_id: int) -> None:
        deleted = await self._repo.delete(category_id, user_id)
        if not deleted:
            raise NotFoundError(f"Category {category_id} not found")


class RenameCategoryUseCase:
    def __init__(self, repo: AbstractCategoryRepository) -> None:
        self._repo = repo

    async def execute(
        self,
        category_id: int,
        user_id: int,
        name: str,
        icon: str | None,
    ) -> CategoryEntity:
        cat = await self._repo.get_by_id(category_id, user_id)
        if not cat:
            raise NotFoundError(f"Category {category_id} not found")
        updated = await self._repo.update(category_id, user_id, name, icon)
        logger.info("Category renamed: user=%d id=%d name=%s", user_id, category_id, name)
        return updated


class GetCategoryUseCase:
    def __init__(self, repo: AbstractCategoryRepository) -> None:
        self._repo = repo

    async def execute(self, category_id: int, user_id: int) -> CategoryEntity:
        cat = await self._repo.get_by_id(category_id, user_id)
        if not cat:
            raise NotFoundError(f"Category {category_id} not found")
        return cat
