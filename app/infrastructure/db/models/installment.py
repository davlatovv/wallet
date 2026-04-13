from datetime import datetime, timezone, date
from decimal import Decimal

from sqlalchemy import BigInteger, Numeric, String, ForeignKey, DateTime, Date, Integer, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.models.base import Base


class Installment(Base):
    __tablename__ = "installments"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    total_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    monthly_payment: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    months_total: Mapped[int] = mapped_column(Integer, nullable=False)
    months_paid: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    next_payment_date: Mapped[date | None] = mapped_column(Date, nullable=True)
    description: Mapped[str | None] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="active", server_default="active")
    # active / completed / cancelled
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship(back_populates="installments", lazy="noload")
