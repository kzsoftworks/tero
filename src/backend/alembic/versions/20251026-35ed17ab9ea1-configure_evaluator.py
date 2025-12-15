"""configure_evaluator

Revision ID: 35ed17ab9ea1
Revises: f688dc4a2a9a
Create Date: 2025-10-26 19:39:36.275516

"""
import sqlalchemy as sa
import sqlmodel
from typing import Sequence, Union
from alembic import op
from sqlalchemy.dialects import postgresql

# revision identifiers, used by Alembic.
revision: str = '35ed17ab9ea1'
down_revision: Union[str, None] = 'f688dc4a2a9a'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table('evaluator',
    sa.Column('id', sa.Integer(), nullable=False),
    sa.Column('model_id', sqlmodel.AutoString(), nullable=False),
    sa.Column('temperature', postgresql.ENUM('CREATIVE', 'NEUTRAL', 'PRECISE', name='llmtemperature', create_type=False), nullable=False),
    sa.Column('reasoning_effort', postgresql.ENUM('LOW', 'MEDIUM', 'HIGH', name='reasoningeffort', create_type=False), nullable=False),
    sa.Column('prompt', sa.Text(), nullable=True),
    sa.Column('created_at', sa.DateTime(), nullable=False),
    sa.ForeignKeyConstraint(['model_id'], ['llm_model.id'], ),
    sa.PrimaryKeyConstraint('id')
    )
    op.create_index('ix_evaluator_model_id', 'evaluator', ['model_id'], unique=False)
    op.add_column('agent', sa.Column('evaluator_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_agent_evaluator_id', 'agent', 'evaluator', ['evaluator_id'], ['id'])
    op.add_column('test_case', sa.Column('evaluator_id', sa.Integer(), nullable=True))
    op.create_foreign_key('fk_test_case_evaluator_id', 'test_case', 'evaluator', ['evaluator_id'], ['id'])

    op.add_column('test_case_result', sa.Column('evaluator_analysis', sa.Text(), nullable=True))


def downgrade() -> None:
    op.drop_column('test_case_result', 'evaluator_analysis')
    
    op.drop_constraint('fk_test_case_evaluator_id', 'test_case', type_='foreignkey')
    op.drop_column('test_case', 'evaluator_id')
    op.drop_constraint('fk_agent_evaluator_id', 'agent', type_='foreignkey')
    op.drop_column('agent', 'evaluator_id')
    op.drop_index('ix_evaluator_model_id', table_name='evaluator')
    op.drop_table('evaluator')
