"""remove consistency signals"""

from alembic import op


revision = "0014_remove_consistency_signals"
down_revision = "0013_expanded_nba_stats"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("DELETE FROM signals WHERE signal_type = 'CONSISTENCY'")


def downgrade() -> None:
    pass
