"""Add transaction currency fields

Revision ID: 0005
Revises: 0004
Create Date: 2026-05-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0005"
down_revision: Union[str, None] = "0004"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("currency", sa.String(length=8), server_default="UZS", nullable=False),
    )
    op.add_column(
        "transactions",
        sa.Column("original_amount", sa.Numeric(15, 2), nullable=True),
    )
    op.add_column(
        "transactions",
        sa.Column("usd_rate", sa.Numeric(15, 2), nullable=True),
    )


def downgrade() -> None:
    op.drop_column("transactions", "usd_rate")
    op.drop_column("transactions", "original_amount")
    op.drop_column("transactions", "currency")
