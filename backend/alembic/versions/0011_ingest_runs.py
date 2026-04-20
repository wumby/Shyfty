"""add ingest_runs table for DB-persisted ingest state

Revision ID: 0011_ingest_runs
Revises: 0010_raw_ingest_events
"""
from alembic import op
import sqlalchemy as sa

revision = "0011_ingest_runs"
down_revision = "0010_raw_ingest_events"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "ingest_runs",
        sa.Column("id", sa.Integer, primary_key=True),
        sa.Column("started_at", sa.DateTime, nullable=False),
        sa.Column("finished_at", sa.DateTime, nullable=True),
        sa.Column("status", sa.String(16), nullable=False, server_default="running"),
        sa.Column("error_message", sa.String(512), nullable=True),
        sa.Column("games_fetched", sa.Integer, nullable=True),
        sa.Column("players_loaded", sa.Integer, nullable=True),
        sa.Column("signals_created", sa.Integer, nullable=True),
        sa.Column("signals_updated", sa.Integer, nullable=True),
        sa.Column("duration_seconds", sa.Float, nullable=True),
    )
    op.create_index("ix_ingest_runs_started_at", "ingest_runs", ["started_at"])
    op.create_index("ix_ingest_runs_status", "ingest_runs", ["status"])


def downgrade() -> None:
    op.drop_index("ix_ingest_runs_status", "ingest_runs")
    op.drop_index("ix_ingest_runs_started_at", "ingest_runs")
    op.drop_table("ingest_runs")
