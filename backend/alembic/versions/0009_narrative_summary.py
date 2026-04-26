"""add narrative_summary to signals

Revision ID: 0009_narrative_summary
Revises: 0008b_signal_engine_upgrade
"""

from alembic import op
import sqlalchemy as sa

revision = "0009_narrative_summary"
down_revision = "0008b_signal_engine_upgrade"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("signals", sa.Column("narrative_summary", sa.String(512), nullable=True))


def downgrade() -> None:
    op.drop_column("signals", "narrative_summary")
