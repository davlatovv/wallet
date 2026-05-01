"""Add Долги category for all users

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-01

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0003"
down_revision: Union[str, None] = "0002"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        INSERT INTO categories (user_id, name, icon, category_type, is_system)
        SELECT u.id, 'Долги', '💳', 'both', true
        FROM users u
        WHERE NOT EXISTS (
            SELECT 1 FROM categories c
            WHERE c.user_id = u.id AND c.name = 'Долги'
        )
    """)


def downgrade() -> None:
    op.execute("""
        DELETE FROM categories
        WHERE name = 'Долги' AND is_system = true AND category_type = 'both'
    """)
