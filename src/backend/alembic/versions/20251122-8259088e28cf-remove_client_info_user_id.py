"""remove_client_info_user_id

Revision ID: 8259088e28cf
Revises: 897df88a29c9
Create Date: 2025-11-22 11:43:38.610593

"""
import sqlalchemy as sa
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '8259088e28cf'
down_revision: Union[str, None] = '897df88a29c9'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.drop_column('tool_oauth_client_info', 'user_id')


def downgrade() -> None:
    op.add_column('tool_oauth_client_info', sa.Column('user_id', sa.INTEGER(), autoincrement=False, nullable=False))
