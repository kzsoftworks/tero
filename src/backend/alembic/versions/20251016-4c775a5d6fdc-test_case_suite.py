"""test_case_suite

Revision ID: 4c775a5d6fdc
Revises: e0ef28b0b663
Create Date: 2025-10-16 17:14:18.736907

"""
import sqlalchemy as sa
from typing import Sequence, Union
from alembic import op
from alembic_postgresql_enum import TableReference
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '4c775a5d6fdc'
down_revision: Union[str, None] = 'e0ef28b0b663'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    sa.Enum('RUNNING', 'SUCCESS', 'FAILURE', name='testsuiterunstatus').create(op.get_bind())
    op.create_table(
        'test_suite_run',
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('agent_id', sa.Integer(), nullable=False),
        sa.Column('status', postgresql.ENUM('RUNNING', 'SUCCESS', 'FAILURE', name='testsuiterunstatus',
                                            create_type=False), nullable=False),
        sa.Column('executed_at', sa.DateTime(), nullable=False),
        sa.Column('completed_at', sa.DateTime(), nullable=True),
        sa.Column('total_tests', sa.Integer(), nullable=False),
        sa.Column('passed_tests', sa.Integer(), nullable=False),
        sa.Column('failed_tests', sa.Integer(), nullable=False),
        sa.Column('error_tests', sa.Integer(), nullable=False),
        sa.Column('skipped_tests', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['agent_id'], ['agent.id'], ),
        sa.PrimaryKeyConstraint('id'))
    op.create_index('ix_test_suite_run_agent_id_executed_at', 'test_suite_run', ['agent_id', 'executed_at'],
                    unique=False)
    op.drop_constraint('test_case_result_pkey', 'test_case_result', type_='primary')
    op.execute('CREATE SEQUENCE test_case_result_id_seq')
    op.add_column('test_case_result', sa.Column('id', sa.Integer(), nullable=True))
    op.execute("UPDATE test_case_result SET id = nextval('test_case_result_id_seq')")
    op.execute("ALTER TABLE test_case_result ALTER COLUMN id SET DEFAULT nextval('test_case_result_id_seq')")
    op.execute("ALTER SEQUENCE test_case_result_id_seq OWNED BY test_case_result.id")
    op.alter_column('test_case_result', 'id',
                    existing_type=sa.INTEGER(),
                    nullable=False)
    op.create_primary_key('test_case_result_pkey', 'test_case_result', ['id'])
    op.alter_column('test_case_result', 'thread_id',
                    existing_type=sa.INTEGER(),
                    nullable=True)
    op.add_column('test_case_result', sa.Column('test_suite_run_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_test_case_result_test_suite_run_id', 'test_case_result', 'test_suite_run',
                          ['test_suite_run_id'], ['id'])
    op.sync_enum_values(  # type: ignore
        enum_schema='public',
        enum_name='testcaseresultstatus',
        new_values=['PENDING', 'RUNNING', 'SUCCESS', 'FAILURE', 'ERROR', 'SKIPPED'],
        affected_columns=[TableReference(table_schema='public', table_name='test_case_result', column_name='status')],
        enum_values_to_rename=[],
    )


def downgrade() -> None:
    op.sync_enum_values(  # type: ignore
        enum_schema='public',
        enum_name='testcaseresultstatus',
        new_values=['PENDING', 'RUNNING', 'SUCCESS', 'FAILURE', 'ERROR'],
        affected_columns=[TableReference(table_schema='public', table_name='test_case_result', column_name='status')],
        enum_values_to_rename=[],
    )
    op.drop_constraint('fk_test_case_result_test_suite_run_id', 'test_case_result', type_='foreignkey')
    op.drop_column('test_case_result', 'test_suite_run_id')
    op.drop_constraint('test_case_result_pkey', 'test_case_result', type_='primary')
    op.drop_column('test_case_result', 'id')
    op.alter_column('test_case_result', 'thread_id',
                    existing_type=sa.INTEGER(),
                    nullable=False)
    op.create_primary_key('test_case_result_pkey', 'test_case_result', ['thread_id'])
    op.drop_index('ix_test_suite_run_agent_id_executed_at', table_name='test_suite_run')
    op.drop_table('test_suite_run')
    sa.Enum('RUNNING', 'SUCCESS', 'FAILURE', name='testsuiterunstatus').drop(op.get_bind())
