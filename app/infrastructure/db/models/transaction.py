from datetime import datetime, timezone
from decimal import Decimal

from sqlalchemy import BigInteger, Numeric, String, ForeignKey, DateTime, Integer, Text, Index
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.models.base import Base


class Transaction(Base):
    __tablename__ = "transactions"

    __table_args__ = (
        Index("ix_transactions_user_created", "user_id", "created_at"),
        Index("ix_transactions_user_type", "user_id", "transaction_type"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    transaction_type: Mapped[str] = mapped_column(String(8), nullable=False)  # income / expense
    currency: Mapped[str] = mapped_column(String(8), default="UZS", server_default="UZS", nullable=False)
    original_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    usd_rate: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    category_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    note: Mapped[str | None] = mapped_column(Text, nullable=True)
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        index=True,
    )

    user: Mapped["User"] = relationship(back_populates="transactions", lazy="noload")
    category: Mapped["Category | None"] = relationship(back_populates="transactions", lazy="noload")
