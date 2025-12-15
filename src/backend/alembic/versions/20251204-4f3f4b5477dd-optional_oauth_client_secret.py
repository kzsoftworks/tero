"""optional_oauth_client_secret

Revision ID: 4f3f4b5477dd
Revises: c759e1cf2817
Create Date: 2025-12-04 10:29:06.934279

"""
import sqlalchemy as sa
from typing import Sequence, Union
from alembic import op


# revision identifiers, used by Alembic.
revision: str = '4f3f4b5477dd'
down_revision: Union[str, None] = 'c759e1cf2817'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.alter_column('tool_oauth_client_info', 'client_secret',
                    existing_type=sa.VARCHAR(),
                    nullable=True)


def downgrade() -> None:
    op.execute("UPDATE tool_oauth_client_info SET client_secret = '' WHERE client_secret IS NULL")
    op.alter_column('tool_oauth_client_info', 'client_secret',
                    existing_type=sa.VARCHAR(),
                    nullable=False)
