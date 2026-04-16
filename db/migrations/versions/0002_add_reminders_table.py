"""Add reminders table

Revision ID: 0002
Revises: 0001
Create Date: 2026-04-16

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0002"
down_revision: Union[str, None] = "0001"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "reminders",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("reminder_type", sa.String(16), nullable=False),
        sa.Column("name", sa.String(256), nullable=False),
        sa.Column("payment_amount", sa.Numeric(15, 2), nullable=False),
        sa.Column("payment_day", sa.SmallInteger(), nullable=False),
        sa.Column("next_payment_date", sa.Date(), nullable=False),
        sa.Column("total_amount", sa.Numeric(15, 2), nullable=True),
        sa.Column("paid_amount", sa.Numeric(15, 2), server_default="0", nullable=False),
        sa.Column("months_total", sa.Integer(), nullable=True),
        sa.Column("months_paid", sa.Integer(), server_default="0", nullable=False),
        sa.Column("interest_rate", sa.Numeric(5, 2), nullable=True),
        sa.Column("payment_type", sa.String(16), nullable=True),
        sa.Column("status", sa.String(16), server_default="active", nullable=False),
        sa.Column("reminder_enabled", sa.Boolean(), server_default="true", nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_reminders_user_id", "reminders", ["user_id"])
    op.create_index("ix_reminders_next_payment_date", "reminders", ["next_payment_date"])
    op.create_index("ix_reminders_user_status", "reminders", ["user_id", "status"])


def downgrade() -> None:
    op.drop_index("ix_reminders_user_status", table_name="reminders")
    op.drop_index("ix_reminders_next_payment_date", table_name="reminders")
    op.drop_index("ix_reminders_user_id", table_name="reminders")
    op.drop_table("reminders")
