from datetime import datetime, timezone, date
from decimal import Decimal

from sqlalchemy import BigInteger, Numeric, String, ForeignKey, DateTime, Date, Integer, Boolean, SmallInteger
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.models.base import Base


class Reminder(Base):
    __tablename__ = "reminders"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    reminder_type: Mapped[str] = mapped_column(String(16), nullable=False)
    # credit / installment / education / regular
    name: Mapped[str] = mapped_column(String(256), nullable=False)
    payment_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), nullable=False)
    payment_day: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    next_payment_date: Mapped[date] = mapped_column(Date, nullable=False)
    total_amount: Mapped[Decimal | None] = mapped_column(Numeric(15, 2), nullable=True)
    paid_amount: Mapped[Decimal] = mapped_column(Numeric(15, 2), default=Decimal("0"), server_default="0")
    months_total: Mapped[int | None] = mapped_column(Integer, nullable=True)
    months_paid: Mapped[int] = mapped_column(Integer, default=0, server_default="0")
    interest_rate: Mapped[Decimal | None] = mapped_column(Numeric(5, 2), nullable=True)
    payment_type: Mapped[str | None] = mapped_column(String(16), nullable=True)
    # annuity / differential
    status: Mapped[str] = mapped_column(String(16), default="active", server_default="active")
    reminder_enabled: Mapped[bool] = mapped_column(Boolean, default=True, server_default="true")
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
    )

    user: Mapped["User"] = relationship(back_populates="reminders", lazy="noload")
