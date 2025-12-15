"""threadmessage-status-update

Revision ID: 897df88a29c9
Revises: 43b41d53f861
Create Date: 2025-11-19 13:43:35.798312

"""
import sqlalchemy as sa
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '897df88a29c9'
down_revision: Union[str, None] = '43b41d53f861'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('thread_message', sa.Column('status_updates', sa.JSON(), nullable=True))


def downgrade() -> None:
    op.drop_column('thread_message', 'status_updates')
