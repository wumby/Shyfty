"""add raw_ingest_events table and player_game_stats idempotency constraint

Revision ID: 0010_raw_ingest_events
Revises: 0009_narrative_summary
"""
from alembic import op
import sqlalchemy as sa

revision = "0010_raw_ingest_events"
down_revision = "0009_narrative_summary"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "raw_ingest_events",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("source", sa.String(64), nullable=False),
        sa.Column("source_type", sa.String(16), nullable=False),
        sa.Column("external_id", sa.String(128), nullable=False),
        sa.Column("event_timestamp", sa.DateTime, nullable=True),
        sa.Column("ingested_at", sa.DateTime, nullable=False),
        sa.Column("raw_payload", sa.Text, nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="processed"),
        sa.UniqueConstraint("source", "external_id", name="uq_raw_ingest_event"),
    )
    op.create_index("ix_raw_ingest_events_source", "raw_ingest_events", ["source"])
    op.create_index("ix_raw_ingest_events_external_id", "raw_ingest_events", ["external_id"])

    # Idempotency guard: each (source_system, source_game_id, source_player_id) must be unique.
    # Uses batch mode for SQLite compatibility (copy-and-move strategy).
    # Safe because the full-reset path always clears player_game_stats before loading,
    # so no duplicate (source_system, source_game_id, source_player_id) exist in existing data.
    with op.batch_alter_table("player_game_stats") as batch_op:
        batch_op.create_unique_constraint(
            "uq_player_game_stat_source",
            ["source_system", "source_game_id", "source_player_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("player_game_stats") as batch_op:
        batch_op.drop_constraint("uq_player_game_stat_source", type_="unique")
    op.drop_index("ix_raw_ingest_events_external_id", "raw_ingest_events")
    op.drop_index("ix_raw_ingest_events_source", "raw_ingest_events")
    op.drop_table("raw_ingest_events")
