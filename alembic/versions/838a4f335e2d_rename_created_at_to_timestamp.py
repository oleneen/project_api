"""rename created_at to timestamp

Revision ID: 838a4f335e2d
Revises: c3b1e8dc0c2b
Create Date: 2025-05-14 18:29:59.840681

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '838a4f335e2d'
down_revision: Union[str, None] = 'c3b1e8dc0c2b'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

def upgrade() -> None:
    # users table
    op.alter_column(
        table_name='users',
        column_name='created_at',
        new_column_name='timestamp'
    )
    # instruments table
    op.alter_column(
        table_name='instruments',
        column_name='created_at',
        new_column_name='timestamp'
    )
    # orders table
    op.alter_column(
        table_name='orders',
        column_name='created_at',
        new_column_name='timestamp'
    )


def downgrade() -> None:
    # revert names back
    op.alter_column(
        table_name='users',
        column_name='timestamp',
        new_column_name='created_at'
    )
    op.alter_column(
        table_name='instruments',
        column_name='timestamp',
        new_column_name='created_at'
    )
    op.alter_column(
        table_name='orders',
        column_name='timestamp',
        new_column_name='created_at'
    )