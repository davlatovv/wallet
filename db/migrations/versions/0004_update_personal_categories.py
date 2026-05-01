"""Update personal categories: rename Жилье, remove Питомцы, add family

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-01

"""
from typing import Sequence, Union

from alembic import op

revision: str = "0004"
down_revision: Union[str, None] = "0003"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("UPDATE categories SET name = 'Дом' WHERE name = 'Жилье'")
    op.execute("DELETE FROM categories WHERE name = 'Питомцы'")
    op.execute("""
        INSERT INTO categories (user_id, name, icon, category_type, is_system)
        SELECT u.id, 'Мама', '👩', 'expense', false
        FROM users u
        WHERE NOT EXISTS (
            SELECT 1 FROM categories c WHERE c.user_id = u.id AND c.name = 'Мама'
        )
    """)
    op.execute("""
        INSERT INTO categories (user_id, name, icon, category_type, is_system)
        SELECT u.id, 'Папа', '👨', 'expense', false
        FROM users u
        WHERE NOT EXISTS (
            SELECT 1 FROM categories c WHERE c.user_id = u.id AND c.name = 'Папа'
        )
    """)
    op.execute("""
        INSERT INTO categories (user_id, name, icon, category_type, is_system)
        SELECT u.id, 'Сестренки', '👧', 'expense', false
        FROM users u
        WHERE NOT EXISTS (
            SELECT 1 FROM categories c WHERE c.user_id = u.id AND c.name = 'Сестренки'
        )
    """)


def downgrade() -> None:
    op.execute("UPDATE categories SET name = 'Жилье' WHERE name = 'Дом'")
    op.execute(
        "DELETE FROM categories WHERE name IN ('Мама', 'Папа', 'Сестренки') AND is_system = false"
    )
