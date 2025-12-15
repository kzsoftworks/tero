"""add_team_editor_role

Revision ID: 6733defeb310
Revises: 8259088e28cf
Create Date: 2025-11-24 14:37:28.062059

"""
from typing import Sequence, Union
from alembic import op
from alembic_postgresql_enum import TableReference

# revision identifiers, used by Alembic.
revision: str = '6733defeb310'
down_revision: Union[str, None] = '8259088e28cf'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.sync_enum_values(  # type: ignore
        enum_schema='public',
        enum_name='role',
        new_values=['TEAM_OWNER', 'TEAM_MEMBER', 'TEAM_EDITOR'],
        affected_columns=[TableReference(table_schema='public', table_name='team_role', column_name='role')],
        enum_values_to_rename=[],
    )


def downgrade() -> None:
    op.sync_enum_values(  # type: ignore
        enum_schema='public',
        enum_name='role',
        new_values=['TEAM_OWNER', 'TEAM_MEMBER'],
        affected_columns=[TableReference(table_schema='public', table_name='team_role', column_name='role')],
        enum_values_to_rename=[],
    )
