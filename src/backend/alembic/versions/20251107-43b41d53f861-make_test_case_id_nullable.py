"""make_test_case_id_nullable

Revision ID: 43b41d53f861
Revises: 9b4a5352b79c
Create Date: 2025-11-07 11:35:15.117154

"""
import sqlalchemy as sa
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '43b41d53f861'
down_revision: Union[str, None] = '9b4a5352b79c'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('test_case_result', 'test_case_id',
               existing_type=sa.INTEGER(),
               nullable=True)


def downgrade() -> None:
    op.execute("""
        DELETE FROM test_case_result
        WHERE test_case_id IS NULL
    """)
    op.alter_column('test_case_result', 'test_case_id',
               existing_type=sa.INTEGER(),
               nullable=False)
