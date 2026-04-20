"""add expanded nba stat columns to player_game_stats

Revision ID: 0013_expanded_nba_stats
Revises: 0012_game_season
"""
import sqlalchemy as sa
from alembic import op

revision = "0013_expanded_nba_stats"
down_revision = "0012_game_season"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("player_game_stats", sa.Column("steals", sa.Integer(), nullable=True))
    op.add_column("player_game_stats", sa.Column("blocks", sa.Integer(), nullable=True))
    op.add_column("player_game_stats", sa.Column("turnovers", sa.Integer(), nullable=True))
    op.add_column("player_game_stats", sa.Column("minutes_played", sa.Float(), nullable=True))
    op.add_column("player_game_stats", sa.Column("plus_minus", sa.Integer(), nullable=True))
    op.add_column("player_game_stats", sa.Column("fg_pct", sa.Float(), nullable=True))
    op.add_column("player_game_stats", sa.Column("fg3_pct", sa.Float(), nullable=True))
    op.add_column("player_game_stats", sa.Column("ft_pct", sa.Float(), nullable=True))


def downgrade() -> None:
    op.drop_column("player_game_stats", "ft_pct")
    op.drop_column("player_game_stats", "fg3_pct")
    op.drop_column("player_game_stats", "fg_pct")
    op.drop_column("player_game_stats", "plus_minus")
    op.drop_column("player_game_stats", "minutes_played")
    op.drop_column("player_game_stats", "turnovers")
    op.drop_column("player_game_stats", "blocks")
    op.drop_column("player_game_stats", "steals")
