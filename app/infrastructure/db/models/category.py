from sqlalchemy import BigInteger, String, ForeignKey, Boolean, Integer
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.infrastructure.db.models.base import Base


class Category(Base):
    __tablename__ = "categories"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, ForeignKey("users.id", ondelete="CASCADE"), index=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    icon: Mapped[str | None] = mapped_column(String(8), nullable=True)
    parent_id: Mapped[int | None] = mapped_column(Integer, ForeignKey("categories.id", ondelete="SET NULL"), nullable=True)
    is_system: Mapped[bool] = mapped_column(Boolean, default=False, server_default="false")
    # income / expense / both
    category_type: Mapped[str] = mapped_column(String(16), default="expense", server_default="expense")

    user: Mapped["User"] = relationship(back_populates="categories", lazy="noload")
    parent: Mapped["Category | None"] = relationship(remote_side="Category.id", lazy="noload")
    children: Mapped[list["Category"]] = relationship(back_populates="parent", lazy="noload")
    transactions: Mapped[list["Transaction"]] = relationship(back_populates="category", lazy="noload")
    budgets: Mapped[list["Budget"]] = relationship(back_populates="category", lazy="noload")
