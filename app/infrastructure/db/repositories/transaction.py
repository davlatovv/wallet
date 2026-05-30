from datetime import datetime
from decimal import Decimal

from sqlalchemy import select, delete, func, extract, case
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import joinedload

from app.domain.entities.transaction import TransactionEntity, TransactionType
from app.domain.repositories.abstract_transaction import AbstractTransactionRepository
from app.infrastructure.db.models.transaction import Transaction
from app.infrastructure.db.models.category import Category


def _to_entity(row: Transaction) -> TransactionEntity:
    return TransactionEntity(
        id=row.id,
        user_id=row.user_id,
        amount=row.amount,
        transaction_type=TransactionType(row.transaction_type),
        category_id=row.category_id,
        note=row.note,
        created_at=row.created_at,
        currency=row.currency,
        original_amount=row.original_amount,
        usd_rate=row.usd_rate,
    )


class SQLAlchemyTransactionRepository(AbstractTransactionRepository):
    def __init__(self, session: AsyncSession) -> None:
        self._session = session

    async def create(
        self,
        user_id: int,
        amount: Decimal,
        transaction_type: TransactionType,
        category_id: int | None,
        note: str | None,
        currency: str = "UZS",
        original_amount: Decimal | None = None,
        usd_rate: Decimal | None = None,
    ) -> TransactionEntity:
        tx = Transaction(
            user_id=user_id,
            amount=amount,
            transaction_type=transaction_type.value,
            category_id=category_id,
            note=note,
            currency=currency,
            original_amount=original_amount,
            usd_rate=usd_rate,
        )
        self._session.add(tx)
        await self._session.flush()
        return _to_entity(tx)

    async def get_by_id(self, transaction_id: int, user_id: int) -> TransactionEntity | None:
        result = await self._session.execute(
            select(Transaction).where(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id,
            )
        )
        row = result.scalar_one_or_none()
        return _to_entity(row) if row else None

    async def list_by_period(
        self,
        user_id: int,
        from_dt: datetime,
        to_dt: datetime,
        transaction_type: TransactionType | None = None,
    ) -> list[TransactionEntity]:
        stmt = (
            select(Transaction, Category.name.label("cat_name"))
            .outerjoin(Category, Transaction.category_id == Category.id)
            .where(
                Transaction.user_id == user_id,
                Transaction.created_at >= from_dt,
                Transaction.created_at <= to_dt,
            )
            .order_by(Transaction.created_at.desc())
        )
        if transaction_type:
            stmt = stmt.where(Transaction.transaction_type == transaction_type.value)
        rows = (await self._session.execute(stmt)).all()
        entities = []
        for tx, cat_name in rows:
            e = _to_entity(tx)
            e.category_name = cat_name
            entities.append(e)
        return entities

    async def list_available_months(self, user_id: int) -> list[tuple[int, int]]:
        year_expr = extract("year", Transaction.created_at).label("year")
        month_expr = extract("month", Transaction.created_at).label("month")
        result = await self._session.execute(
            select(year_expr, month_expr)
            .where(Transaction.user_id == user_id)
            .group_by(year_expr, month_expr)
            .order_by(year_expr.desc(), month_expr.desc())
        )
        return [(int(row.year), int(row.month)) for row in result.all()]

    async def delete(self, transaction_id: int, user_id: int) -> bool:
        result = await self._session.execute(
            delete(Transaction).where(
                Transaction.id == transaction_id,
                Transaction.user_id == user_id,
            )
        )
        return result.rowcount > 0

    async def sum_by_period(
        self,
        user_id: int,
        from_dt: datetime,
        to_dt: datetime,
        transaction_type: TransactionType,
    ) -> Decimal:
        result = await self._session.execute(
            select(func.coalesce(func.sum(Transaction.amount), 0)).where(
                Transaction.user_id == user_id,
                Transaction.transaction_type == transaction_type.value,
                Transaction.created_at >= from_dt,
                Transaction.created_at <= to_dt,
            )
        )
        return Decimal(str(result.scalar_one()))

    async def sum_by_category(
        self,
        user_id: int,
        from_dt: datetime,
        to_dt: datetime,
        transaction_type: TransactionType,
    ) -> list[tuple[int, str, Decimal]]:
        result = await self._session.execute(
            select(
                Category.id,
                Category.name,
                func.sum(Transaction.amount).label("total"),
            )
            .join(Category, Transaction.category_id == Category.id)
            .where(
                Transaction.user_id == user_id,
                Transaction.transaction_type == transaction_type.value,
                Transaction.created_at >= from_dt,
                Transaction.created_at <= to_dt,
            )
            .group_by(Category.id, Category.name)
            .order_by(func.sum(Transaction.amount).desc())
        )
        return [(row.id, row.name, Decimal(str(row.total))) for row in result.all()]

    async def sum_balance_by_currency(
        self,
        user_id: int,
        from_dt: datetime,
        to_dt: datetime,
    ) -> list[tuple[str, Decimal]]:
        currency_expr = func.coalesce(Transaction.currency, "UZS").label("currency")
        signed_amount = case(
            (Transaction.transaction_type == TransactionType.INCOME.value, Transaction.amount),
            else_=-Transaction.amount,
        )
        result = await self._session.execute(
            select(
                currency_expr,
                func.coalesce(func.sum(signed_amount), 0).label("total"),
            )
            .where(
                Transaction.user_id == user_id,
                Transaction.created_at >= from_dt,
                Transaction.created_at <= to_dt,
            )
            .group_by(currency_expr)
        )
        return [(row.currency, Decimal(str(row.total))) for row in result.all()]
