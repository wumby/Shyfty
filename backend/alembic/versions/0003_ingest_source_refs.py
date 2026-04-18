"""add source references for ingested entities"""

from alembic import op
import sqlalchemy as sa

revision = "0003_ingest_source_refs"
down_revision = "0002_signal_generation_context"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("teams") as batch_op:
        batch_op.add_column(sa.Column("source_system", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("source_id", sa.String(length=64), nullable=True))

    with op.batch_alter_table("players") as batch_op:
        batch_op.add_column(sa.Column("source_system", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("source_id", sa.String(length=64), nullable=True))

    with op.batch_alter_table("games") as batch_op:
        batch_op.add_column(sa.Column("source_system", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("source_id", sa.String(length=64), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("games") as batch_op:
        batch_op.drop_column("source_id")
        batch_op.drop_column("source_system")

    with op.batch_alter_table("players") as batch_op:
        batch_op.drop_column("source_id")
        batch_op.drop_column("source_system")

    with op.batch_alter_table("teams") as batch_op:
        batch_op.drop_column("source_id")
        batch_op.drop_column("source_system")
