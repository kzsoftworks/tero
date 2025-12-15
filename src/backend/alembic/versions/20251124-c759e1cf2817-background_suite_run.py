"""background_suite_run

Revision ID: c759e1cf2817
Revises: 6733defeb310
Create Date: 2025-11-24 15:54:42.406436

"""

import sqlalchemy as sa
import sqlmodel
from typing import Sequence, Union
from alembic import op
from alembic_postgresql_enum import TableReference

# revision identifiers, used by Alembic.
revision: str = "c759e1cf2817"
down_revision: Union[str, None] = "6733defeb310"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "test_suite_run_event",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("test_suite_run_id", sa.Integer(), nullable=False),
        sa.Column("type", sqlmodel.AutoString(), nullable=False),
        sa.Column("data", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(
            ["test_suite_run_id"],
            ["test_suite_run.id"],
        ),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(
        "ix_test_suite_run_event_test_suite_run_id_created_at",
        "test_suite_run_event",
        ["test_suite_run_id", "created_at"],
        unique=False,
    )
    op.sync_enum_values(  # type: ignore[attr-defined]
        enum_schema="public",
        enum_name="testsuiterunstatus",
        new_values=["RUNNING", "SUCCESS", "FAILURE", "CANCELLING"],
        affected_columns=[
            TableReference(
                table_schema="public", table_name="test_suite_run", column_name="status"
            )
        ],
        enum_values_to_rename=[],
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION notify_test_suite_run_event() RETURNS TRIGGER AS $$
        BEGIN
            PERFORM pg_notify(
                'test_suite_events',
                json_build_object(
                    'suite_run_id', NEW.test_suite_run_id,
                    'event_id', NEW.id
                )::text
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    op.execute(
        """
        CREATE TRIGGER after_insert_test_suite_run_event
        AFTER INSERT ON test_suite_run_event
        FOR EACH ROW EXECUTE FUNCTION notify_test_suite_run_event();
    """
    )

    op.execute(
        """
        CREATE OR REPLACE FUNCTION notify_test_suite_run_status() RETURNS TRIGGER AS $$
        BEGIN
            PERFORM pg_notify(
                'test_suite_status',
                json_build_object(
                    'suite_run_id', NEW.id,
                    'status', NEW.status
                )::text
            );
            RETURN NEW;
        END;
        $$ LANGUAGE plpgsql;
    """
    )

    op.execute(
        """
        CREATE TRIGGER after_update_test_suite_run_status
        AFTER UPDATE OF status ON test_suite_run
        FOR EACH ROW 
        WHEN (OLD.status IS DISTINCT FROM NEW.status)
        EXECUTE FUNCTION notify_test_suite_run_status();
    """
    )


def downgrade() -> None:
    op.execute(
        "DROP TRIGGER IF EXISTS after_update_test_suite_run_status ON test_suite_run"
    )
    op.execute("DROP FUNCTION IF EXISTS notify_test_suite_run_status()")
    op.execute(
        "DROP TRIGGER IF EXISTS after_insert_test_suite_run_event ON test_suite_run_event"
    )
    op.execute("DROP FUNCTION IF EXISTS notify_test_suite_run_event()")

    op.sync_enum_values(  # type: ignore[attr-defined]
        enum_schema="public",
        enum_name="testsuiterunstatus",
        new_values=["RUNNING", "SUCCESS", "FAILURE"],
        affected_columns=[
            TableReference(
                table_schema="public", table_name="test_suite_run", column_name="status"
            )
        ],
        enum_values_to_rename=[],
    )
    op.drop_index(
        "ix_test_suite_run_event_test_suite_run_id_created_at",
        table_name="test_suite_run_event",
    )
    op.drop_table("test_suite_run_event")
