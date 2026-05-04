"""Expand NFL player/team box score fields.

Revision ID: 0017_expand_nfl_box_score_fields
Revises: 0016_sync_checkpoints
Create Date: 2026-05-01 22:00:00.000000
"""

from alembic import op
import sqlalchemy as sa


revision = "0017_expand_nfl_box_score_fields"
down_revision = "0016_sync_checkpoints"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("player_game_stats", sa.Column("passing_completions", sa.Integer(), nullable=True))
    op.add_column("player_game_stats", sa.Column("passing_attempts", sa.Integer(), nullable=True))
    op.add_column("player_game_stats", sa.Column("interceptions", sa.Integer(), nullable=True))
    op.add_column("player_game_stats", sa.Column("rushing_attempts", sa.Integer(), nullable=True))
    op.add_column("player_game_stats", sa.Column("receptions", sa.Integer(), nullable=True))
    op.add_column("player_game_stats", sa.Column("targets", sa.Integer(), nullable=True))
    op.add_column("player_game_stats", sa.Column("sacks", sa.Integer(), nullable=True))
    op.add_column("player_game_stats", sa.Column("fumbles_lost", sa.Integer(), nullable=True))

    op.add_column("team_game_stats", sa.Column("total_yards", sa.Integer(), nullable=True))
    op.add_column("team_game_stats", sa.Column("first_downs", sa.Integer(), nullable=True))
    op.add_column("team_game_stats", sa.Column("penalties", sa.Integer(), nullable=True))
    op.add_column("team_game_stats", sa.Column("penalty_yards", sa.Integer(), nullable=True))
    op.add_column("team_game_stats", sa.Column("turnovers_forced", sa.Integer(), nullable=True))
    op.add_column("team_game_stats", sa.Column("turnovers_lost", sa.Integer(), nullable=True))
    op.add_column("team_game_stats", sa.Column("third_down_pct", sa.Float(), nullable=True))
    op.add_column("team_game_stats", sa.Column("redzone_pct", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("team_game_stats", "redzone_pct")
    op.drop_column("team_game_stats", "third_down_pct")
    op.drop_column("team_game_stats", "turnovers_lost")
    op.drop_column("team_game_stats", "turnovers_forced")
    op.drop_column("team_game_stats", "penalty_yards")
    op.drop_column("team_game_stats", "penalties")
    op.drop_column("team_game_stats", "first_downs")
    op.drop_column("team_game_stats", "total_yards")

    op.drop_column("player_game_stats", "fumbles_lost")
    op.drop_column("player_game_stats", "sacks")
    op.drop_column("player_game_stats", "targets")
    op.drop_column("player_game_stats", "receptions")
    op.drop_column("player_game_stats", "rushing_attempts")
    op.drop_column("player_game_stats", "interceptions")
    op.drop_column("player_game_stats", "passing_attempts")
    op.drop_column("player_game_stats", "passing_completions")
