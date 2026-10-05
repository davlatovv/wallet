from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import BigInteger, String, DateTime, Numeric
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.models.base import Base


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(BigInteger, primary_key=True)  # telegram_id
    username: Mapped[str | None] = mapped_column(String(64), nullable=True)
    first_name: Mapped[str | None] = mapped_column(String(128), nullable=True)
    timezone: Mapped[str] = mapped_column(String(64), default="UTC", server_default="UTC")
    cash_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, server_default="0", nullable=False)
    card_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, server_default="0", nullable=False)
    currency_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, server_default="0", nullable=False)
    total_balance: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=0, server_default="0", nullable=False)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    transactions: Mapped[list["Transaction"]] = relationship(back_populates="user", lazy="noload")
    categories: Mapped[list["Category"]] = relationship(back_populates="user", lazy="noload")
    budgets: Mapped[list["Budget"]] = relationship(back_populates="user", lazy="noload")
    debts: Mapped[list["Debt"]] = relationship(back_populates="user", lazy="noload")
    savings_goals: Mapped[list["SavingsGoal"]] = relationship(back_populates="user", lazy="noload")
    reminders: Mapped[list["Reminder"]] = relationship(back_populates="user", lazy="noload")
