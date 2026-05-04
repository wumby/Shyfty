"""add schedule-first game sync fields

Revision ID: 0019_schedule_first_sync
Revises: 0018_shyft_reactions
Create Date: 2026-05-04
"""

from alembic import op
import sqlalchemy as sa


revision = "0019_schedule_first_sync"
down_revision = "0018_shyft_reactions"
branch_labels = None
depends_on = None


def _column_exists(table_name: str, column_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(col["name"] == column_name for col in inspector.get_columns(table_name))


def _index_exists(table_name: str, index_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(idx["name"] == index_name for idx in inspector.get_indexes(table_name))


def _unique_constraint_exists(table_name: str, constraint_name: str) -> bool:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    return any(c["name"] == constraint_name for c in inspector.get_unique_constraints(table_name))


def upgrade() -> None:
    bind = op.get_bind()
    is_sqlite = bind.dialect.name == "sqlite"
    if not _column_exists("games", "external_game_id"):
        op.add_column("games", sa.Column("external_game_id", sa.String(length=64), nullable=True))
    if not _column_exists("games", "status"):
        op.add_column("games", sa.Column("status", sa.String(length=16), nullable=False, server_default="unknown"))
    if not _column_exists("games", "home_team_external_id"):
        op.add_column("games", sa.Column("home_team_external_id", sa.String(length=64), nullable=True))
    if not _column_exists("games", "away_team_external_id"):
        op.add_column("games", sa.Column("away_team_external_id", sa.String(length=64), nullable=True))
    if not _column_exists("games", "last_hydrated_at"):
        op.add_column("games", sa.Column("last_hydrated_at", sa.DateTime(), nullable=True))
    if not _column_exists("games", "source_updated_at"):
        op.add_column("games", sa.Column("source_updated_at", sa.DateTime(), nullable=True))
    if not _column_exists("games", "raw_schedule_payload"):
        op.add_column("games", sa.Column("raw_schedule_payload", sa.Text(), nullable=True))
    if not _index_exists("games", "ix_games_external_game_id"):
        op.create_index("ix_games_external_game_id", "games", ["external_game_id"])

    op.execute("UPDATE games SET external_game_id = source_id WHERE external_game_id IS NULL")
    if is_sqlite:
        if not _index_exists("games", "uq_games_league_external_game_id"):
            op.create_index(
                "uq_games_league_external_game_id",
                "games",
                ["league_id", "external_game_id"],
                unique=True,
            )
    elif not _unique_constraint_exists("games", "uq_games_league_external_game_id"):
        op.create_unique_constraint(
            "uq_games_league_external_game_id",
            "games",
            ["league_id", "external_game_id"],
        )

    if not is_sqlite:
        op.alter_column("games", "status", server_default=None)


def downgrade() -> None:
    op.drop_constraint("uq_games_league_external_game_id", "games", type_="unique")
    op.drop_index("ix_games_external_game_id", table_name="games")
    op.drop_column("games", "raw_schedule_payload")
    op.drop_column("games", "source_updated_at")
    op.drop_column("games", "last_hydrated_at")
    op.drop_column("games", "away_team_external_id")
    op.drop_column("games", "home_team_external_id")
    op.drop_column("games", "status")
    op.drop_column("games", "external_game_id")
