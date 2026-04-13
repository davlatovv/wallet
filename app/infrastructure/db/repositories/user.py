from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.abstract_user import AbstractUserRepository
from app.infrastructure.db.models.user import User


class SQLAlchemyUserRepository(AbstractUserRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def get_or_create(self, telegram_id: int, username: str | None, first_name: str | None) -> bool:
        result = await self._session.execute(select(User).where(User.id == telegram_id))
        user = result.scalar_one_or_none()
        if user:
            return False
        user = User(id=telegram_id, username=username, first_name=first_name)
        self._session.add(user)
        await self._session.flush()
        return True

    async def exists(self, telegram_id: int) -> bool:
        result = await self._session.execute(select(User.id).where(User.id == telegram_id))
        return result.scalar_one_or_none() is not None
