from sqlalchemy import select, update, delete
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.entities.category import CategoryEntity
from app.domain.repositories.abstract_category import AbstractCategoryRepository
from app.infrastructure.db.models.category import Category

DEFAULT_EXPENSE_CATEGORIES = [
    ("🍔", "Еда"),
    ("🚗", "Транспорт"),
    ("👨‍👩‍👧", "Семья"),
    ("💊", "Здоровье"),
    ("👗", "Одежда"),
    ("🎮", "Развлечения"),
    ("📚", "Образование"),
    ("📱", "Связь"),
    ("💡", "Коммунальные"),
    ("🎁", "Подарки"),
    ("✈️", "Путешествия"),
    ("🏋️", "Спорт"),
    ("💈", "Красота"),
    ("📦", "Прочее"),
]

DEFAULT_INCOME_CATEGORIES = [
    ("💼", "Зарплата"),
    ("📈", "Инвестиции"),
    ("🤝", "Фриланс"),
    ("🎁", "Подарки"),
    ("💰", "Прочий доход"),
]


def _to_entity(row: Category) -> CategoryEntity:
    return CategoryEntity(
        id=row.id,
        user_id=row.user_id,
        name=row.name,
        icon=row.icon,
        parent_id=row.parent_id,
        is_system=row.is_system,
        category_type=row.category_type,
    )


class SQLAlchemyCategoryRepository(AbstractCategoryRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(self, user_id, name, icon, parent_id, category_type) -> CategoryEntity:
        cat = Category(
            user_id=user_id,
            name=name,
            icon=icon,
            parent_id=parent_id,
            category_type=category_type,
            is_system=False,
        )
        self._session.add(cat)
        await self._session.flush()
        return _to_entity(cat)

    async def get_by_id(self, category_id: int, user_id: int) -> CategoryEntity | None:
        result = await self._session.execute(
            select(Category).where(Category.id == category_id, Category.user_id == user_id)
        )
        row = result.scalar_one_or_none()
        return _to_entity(row) if row else None

    async def list_by_user(self, user_id: int, category_type: str | None = None) -> list[CategoryEntity]:
        stmt = select(Category).where(Category.user_id == user_id).order_by(Category.name)
        if category_type:
            stmt = stmt.where(Category.category_type.in_([category_type, "both"]))
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(r) for r in rows]

    async def list_root(self, user_id: int, category_type: str | None = None) -> list[CategoryEntity]:
        stmt = (
            select(Category)
            .where(Category.user_id == user_id, Category.parent_id.is_(None))
            .order_by(Category.name)
        )
        if category_type:
            stmt = stmt.where(Category.category_type.in_([category_type, "both"]))
        rows = (await self._session.execute(stmt)).scalars().all()
        return [_to_entity(r) for r in rows]

    async def list_children(self, user_id: int, parent_id: int) -> list[CategoryEntity]:
        rows = (
            await self._session.execute(
                select(Category).where(
                    Category.user_id == user_id,
                    Category.parent_id == parent_id,
                )
            )
        ).scalars().all()
        return [_to_entity(r) for r in rows]

    async def update(self, category_id: int, user_id: int, name: str, icon: str | None) -> CategoryEntity | None:
        await self._session.execute(
            update(Category)
            .where(Category.id == category_id, Category.user_id == user_id)
            .values(name=name, icon=icon)
        )
        return await self.get_by_id(category_id, user_id)

    async def delete(self, category_id: int, user_id: int) -> bool:
        result = await self._session.execute(
            delete(Category).where(Category.id == category_id, Category.user_id == user_id)
        )
        return result.rowcount > 0

    async def seed_defaults(self, user_id: int) -> None:
        for icon, name in DEFAULT_EXPENSE_CATEGORIES:
            cat = Category(user_id=user_id, name=name, icon=icon, category_type="expense", is_system=True)
            self._session.add(cat)
        for icon, name in DEFAULT_INCOME_CATEGORIES:
            cat = Category(user_id=user_id, name=name, icon=icon, category_type="income", is_system=True)
            self._session.add(cat)
        await self._session.flush()
