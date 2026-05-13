"""add indexes for retention prune queries

Revision ID: 0024_add_retention_prune_indexes
Revises: 0023_cleanup_legacy_signal_tables
Create Date: 2026-05-12
"""

from alembic import op

revision = "0024_add_retention_prune_indexes"
down_revision = "0023_cleanup_legacy_signal_tables"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_index("ix_games_game_date", "games", ["game_date"], unique=False)
    op.create_index("ix_raw_ingest_events_ingested_at", "raw_ingest_events", ["ingested_at"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_raw_ingest_events_ingested_at", table_name="raw_ingest_events")
    op.drop_index("ix_games_game_date", table_name="games")
