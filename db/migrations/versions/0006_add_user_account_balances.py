"""Add user account balances

Revision ID: 0006
Revises: 0005
Create Date: 2026-05-30

"""
from typing import Sequence, Union

import sqlalchemy as sa
from alembic import op

revision: str = "0006"
down_revision: Union[str, None] = "0005"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "transactions",
        sa.Column("account_type", sa.String(length=16), server_default="card", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("cash_balance", sa.Numeric(15, 2), server_default="0", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("card_balance", sa.Numeric(15, 2), server_default="0", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("currency_balance", sa.Numeric(15, 2), server_default="0", nullable=False),
    )
    op.add_column(
        "users",
        sa.Column("total_balance", sa.Numeric(15, 2), server_default="0", nullable=False),
    )

    op.execute(
        """
        UPDATE transactions
        SET account_type = CASE
            WHEN currency = 'CASH' THEN 'cash'
            WHEN currency = 'USD' THEN 'currency'
            ELSE 'card'
        END
        """
    )
    op.execute(
        """
        WITH signed_transactions AS (
            SELECT
                user_id,
                account_type,
                CASE
                    WHEN transaction_type = 'income' THEN amount
                    ELSE -amount
                END AS signed_amount
            FROM transactions
        ),
        totals AS (
            SELECT
                user_id,
                COALESCE(SUM(CASE WHEN account_type = 'cash' THEN signed_amount ELSE 0 END), 0) AS cash_balance,
                COALESCE(SUM(CASE WHEN account_type = 'card' THEN signed_amount ELSE 0 END), 0) AS card_balance,
                COALESCE(SUM(CASE WHEN account_type = 'currency' THEN signed_amount ELSE 0 END), 0) AS currency_balance,
                COALESCE(SUM(signed_amount), 0) AS total_balance
            FROM signed_transactions
            GROUP BY user_id
        )
        UPDATE users
        SET
            cash_balance = totals.cash_balance,
            card_balance = totals.card_balance,
            currency_balance = totals.currency_balance,
            total_balance = totals.total_balance
        FROM totals
        WHERE users.id = totals.user_id
        """
    )


def downgrade() -> None:
    op.drop_column("users", "total_balance")
    op.drop_column("users", "currency_balance")
    op.drop_column("users", "card_balance")
    op.drop_column("users", "cash_balance")
    op.drop_column("transactions", "account_type")
