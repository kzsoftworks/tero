"""fix-global-team-name

Revision ID: f688dc4a2a9a
Revises: 07fd1bcafad1
Create Date: 2025-11-17 14:10:08.496924

"""
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = 'f688dc4a2a9a'
down_revision: Union[str, None] = '07fd1bcafad1'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("""
        UPDATE team
        SET name = 'Global'
        WHERE id = 1
    """)


def downgrade() -> None:
    op.execute("""
        UPDATE team
        SET name = 'Default'
        WHERE id = 1
    """)
