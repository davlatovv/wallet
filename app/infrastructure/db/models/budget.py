from datetime import date
from decimal import Decimal

from sqlalchemy import BigInteger, Numeric, String, ForeignKey, Date, Integer, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.models.base import Base


class Budget(Base):
    __tablename__ = "budgets"

    __table_args__ = (
        Index("ix_budgets_user_category", "user_id", "category_id"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("categories.id", ondelete="CASCADE"), nullable=True)
    limit_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    period: Mapped[str] = mapped_column(String(16), nullable=False)  # monthly / weekly / daily
    start_date: Mapped[date] = mapped_column(Date, nullable=False)

    user: Mapped["User"] = relationship(back_populates="budgets", lazy="noload")
    category: Mapped["Category | None"] = relationship(back_populates="budgets", lazy="noload")
