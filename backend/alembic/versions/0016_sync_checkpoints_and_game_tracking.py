"""add sync checkpoints and game sync tracking

Revision ID: 0016_sync_checkpoints_and_game_tracking
Revises: 0015_team_game_stats_and_team_signals
Create Date: 2026-04-23
"""

from alembic import op
import sqlalchemy as sa


revision = "0016_sync_checkpoints_and_game_tracking"
down_revision = "0015_team_game_stats_and_team_signals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("games", sa.Column("last_synced_at", sa.DateTime(), nullable=True))
    op.add_column("games", sa.Column("signals_generated_at", sa.DateTime(), nullable=True))

    op.create_table(
        "sync_checkpoints",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("source", sa.String(length=64), nullable=False),
        sa.Column("checkpoint_key", sa.String(length=64), nullable=False),
        sa.Column("checkpoint_value", sa.String(length=255), nullable=True),
        sa.Column("checkpoint_metadata", sa.Text(), nullable=True),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("source", "checkpoint_key", name="uq_sync_checkpoint_source_key"),
    )
    op.create_index("ix_sync_checkpoints_source", "sync_checkpoints", ["source"])


def downgrade() -> None:
    op.drop_index("ix_sync_checkpoints_source", table_name="sync_checkpoints")
    op.drop_table("sync_checkpoints")
    op.drop_column("games", "signals_generated_at")
    op.drop_column("games", "last_synced_at")
