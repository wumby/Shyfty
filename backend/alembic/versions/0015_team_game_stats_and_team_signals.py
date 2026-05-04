"""add team_game_stats and team signal support"""

from alembic import op
import sqlalchemy as sa


revision = "0015_team_game_stats"
down_revision = "0014_remove_consistency_signals"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "team_game_stats",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=False),
        sa.Column("game_id", sa.Integer(), sa.ForeignKey("games.id"), nullable=False),
        sa.Column("opponent_team_id", sa.Integer(), sa.ForeignKey("teams.id"), nullable=True),
        sa.Column("opponent_name", sa.String(length=64), nullable=True),
        sa.Column("home_away", sa.String(length=8), nullable=True),
        sa.Column("points", sa.Integer(), nullable=True),
        sa.Column("rebounds", sa.Integer(), nullable=True),
        sa.Column("assists", sa.Integer(), nullable=True),
        sa.Column("fg_pct", sa.Float(), nullable=True),
        sa.Column("fg3_pct", sa.Float(), nullable=True),
        sa.Column("turnovers", sa.Integer(), nullable=True),
        sa.Column("pace", sa.Float(), nullable=True),
        sa.Column("off_rating", sa.Float(), nullable=True),
        sa.Column("source_system", sa.String(length=32), nullable=True),
        sa.Column("source_game_id", sa.String(length=64), nullable=True),
        sa.Column("source_team_id", sa.String(length=64), nullable=True),
        sa.Column("raw_snapshot_path", sa.String(length=255), nullable=True),
        sa.Column("raw_traditional_payload_path", sa.String(length=255), nullable=True),
        sa.Column("raw_advanced_payload_path", sa.String(length=255), nullable=True),
        sa.Column("raw_record_index", sa.Integer(), nullable=True),
        sa.UniqueConstraint("source_system", "source_game_id", "source_team_id", name="uq_team_game_stat_source"),
    )

    with op.batch_alter_table("signals") as batch_op:
        batch_op.alter_column("player_id", existing_type=sa.Integer(), nullable=True)
        batch_op.add_column(sa.Column("source_team_stat_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("subject_type", sa.String(length=16), nullable=False, server_default="player"))
        batch_op.create_foreign_key(
            "fk_signals_source_team_stat_id_team_game_stats",
            "team_game_stats",
            ["source_team_stat_id"],
            ["id"],
        )

    op.execute("UPDATE signals SET subject_type = 'player' WHERE subject_type IS NULL")


def downgrade() -> None:
    with op.batch_alter_table("signals") as batch_op:
        batch_op.drop_constraint("fk_signals_source_team_stat_id_team_game_stats", type_="foreignkey")
        batch_op.drop_column("subject_type")
        batch_op.drop_column("source_team_stat_id")
        batch_op.alter_column("player_id", existing_type=sa.Integer(), nullable=False)

    op.drop_table("team_game_stats")
