"""add season column to games, backfill from game_date

Revision ID: 0012_game_season
Revises: 0011_ingest_runs
"""
from datetime import date

import sqlalchemy as sa
from alembic import op

revision = "0012_game_season"
down_revision = "0011_ingest_runs"
branch_labels = None
depends_on = None


def _season_from_date(game_date: date) -> str:
    if game_date.month >= 10:
        start = game_date.year
    else:
        start = game_date.year - 1
    return f"{start}-{str(start + 1)[-2:]}"


def upgrade() -> None:
    op.add_column("games", sa.Column("season", sa.String(7), nullable=True))

    bind = op.get_bind()
    rows = bind.execute(sa.text("SELECT id, game_date FROM games")).fetchall()
    for row_id, raw_date in rows:
        if isinstance(raw_date, str):
            game_date = date.fromisoformat(raw_date)
        else:
            game_date = raw_date
        bind.execute(
            sa.text("UPDATE games SET season = :season WHERE id = :id"),
            {"season": _season_from_date(game_date), "id": row_id},
        )

    op.create_index("ix_games_season", "games", ["season"])


def downgrade() -> None:
    op.drop_index("ix_games_season", "games")
    op.drop_column("games", "season")
