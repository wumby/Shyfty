"""initial schema"""

from alembic import op
import sqlalchemy as sa

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table("leagues", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(length=16), nullable=False, unique=True))
    op.create_table("teams", sa.Column("id", sa.Integer(), primary_key=True), sa.Column("name", sa.String(length=64), nullable=False), sa.Column("league_id", sa.Integer(), sa.ForeignKey("leagues.id"), nullable=False))
    op.create_table(
        "players",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("name", sa.String(length=128), nullable=False),
        sa.Column("league_id", sa.Integer(), sa.ForeignKey("leagues.id"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("position", sa.String(length=32), nullable=False),
    )
    op.create_table(
        "games",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("league_id", sa.Integer(), sa.ForeignKey("leagues.id"), nullable=False),
        sa.Column("game_date", sa.Date(), nullable=False),
        sa.Column("home_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("away_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
    )
    op.create_table(
        "player_game_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("games.id"), nullable=False),
        sa.Column("points", sa.Integer(), nullable=True),
        sa.Column("rebounds", sa.Integer(), nullable=True),
        sa.Column("assists", sa.Integer(), nullable=True),
        sa.Column("passing_yards", sa.Integer(), nullable=True),
        sa.Column("rushing_yards", sa.Integer(), nullable=True),
        sa.Column("receiving_yards", sa.Integer(), nullable=True),
        sa.Column("touchdowns", sa.Integer(), nullable=True),
        sa.Column("usage_rate", sa.Float(), nullable=True),
    )
    op.create_table(
        "rolling_metrics",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("metric_name", sa.String(length=64), nullable=False),
        sa.Column("rolling_avg", sa.Float(), nullable=False),
        sa.Column("rolling_stddev", sa.Float(), nullable=False),
        sa.Column("z_score", sa.Float(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.UniqueConstraint("player_id", "metric_name", name="uq_player_metric"),
    )
    op.create_table(
        "signals",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("player_id", sa.Integer(), sa.ForeignKey("players.id"), nullable=False),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("league_id", sa.Integer(), sa.ForeignKey("leagues.id"), nullable=False),
        sa.Column("signal_type", sa.String(length=32), nullable=False),
        sa.Column("metric_name", sa.String(length=64), nullable=False),
        sa.Column("current_value", sa.Float(), nullable=False),
        sa.Column("baseline_value", sa.Float(), nullable=False),
        sa.Column("z_score", sa.Float(), nullable=False),
        sa.Column("explanation", sa.String(length=255), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("signals")
    op.drop_table("rolling_metrics")
    op.drop_table("player_game_stats")
    op.drop_table("games")
    op.drop_table("players")
    op.drop_table("teams")
    op.drop_table("leagues")
