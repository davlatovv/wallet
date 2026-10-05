from decimal import Decimal

from sqlalchemy import select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.domain.repositories.abstract_user import AbstractUserRepository
from app.domain.entities.transaction import AccountType
from app.domain.entities.user import UserBalanceEntity
from app.infrastructure.db.models.user import User


def _to_balance(row: User) -> UserBalanceEntity:
    return UserBalanceEntity(
        user_id=row.id,
        cash_balance=row.cash_balance,
        card_balance=row.card_balance,
        currency_balance=row.currency_balance,
        total_balance=row.total_balance,
    )


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

    async def get_timezone(self, user_id: int) -> str | None:
        result = await self._session.execute(select(User.timezone).where(User.id == user_id))
        return result.scalar_one_or_none()

    async def update_timezone(self, user_id: int, timezone: str) -> str | None:
        result = await self._session.execute(
            update(User).where(User.id == user_id).values(timezone=timezone).returning(User.timezone)
        )
        row = result.scalar_one_or_none()
        return row

    async def get_balance(self, user_id: int) -> UserBalanceEntity | None:
        result = await self._session.execute(select(User).where(User.id == user_id))
        user = result.scalar_one_or_none()
        return _to_balance(user) if user else None

    async def apply_balance_delta(
        self,
        user_id: int,
        account_type: AccountType,
        amount_delta: Decimal,
    ) -> UserBalanceEntity | None:
        values = {
            User.total_balance: User.total_balance + amount_delta,
        }
        if account_type == AccountType.CASH:
            values[User.cash_balance] = User.cash_balance + amount_delta
        elif account_type == AccountType.CURRENCY:
            values[User.currency_balance] = User.currency_balance + amount_delta
        else:
            values[User.card_balance] = User.card_balance + amount_delta

        await self._session.execute(update(User).where(User.id == user_id).values(values))
        return await self.get_balance(user_id)
