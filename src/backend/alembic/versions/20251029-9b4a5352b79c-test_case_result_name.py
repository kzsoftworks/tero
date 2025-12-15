"""test_case_result_name

Revision ID: 9b4a5352b79c
Revises: 35ed17ab9ea1
Create Date: 2025-10-29 12:26:46.957655

"""
import sqlalchemy as sa
import sqlmodel
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '9b4a5352b79c'
down_revision: Union[str, None] = '35ed17ab9ea1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('test_case_result', sa.Column('test_case_name', sqlmodel.AutoString(), nullable=True))
    
    op.execute("""
        UPDATE test_case_result
        SET test_case_name = thread.name
        FROM thread
        WHERE thread.id = test_case_result.test_case_id
    """)


def downgrade() -> None:
    op.drop_column('test_case_result', 'test_case_name')
