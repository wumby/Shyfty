"""upgrade rolling metrics and signals for scored multi-window engine"""

from alembic import op
import sqlalchemy as sa

revision = "0007_signal_engine_upgrade"
down_revision = "0008_personalization_and_comment_moderation"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("rolling_metrics") as batch_op:
        batch_op.add_column(sa.Column("short_window_size", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("medium_window_size", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("season_window_size", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("short_values", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("medium_values", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("season_values", sa.JSON(), nullable=True))
        batch_op.add_column(sa.Column("short_rolling_avg", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("short_rolling_stddev", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("short_z_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("medium_rolling_avg", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("medium_rolling_stddev", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("medium_z_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("season_rolling_avg", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("season_rolling_stddev", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("season_z_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("ewma", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("recent_delta", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("trend_slope", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("volatility_index", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("volatility_delta", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("opponent_average_allowed", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("opponent_rank", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("pace_proxy", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("usage_shift", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("high_volatility", sa.Boolean(), nullable=True))

    with op.batch_alter_table("signals") as batch_op:
        batch_op.add_column(sa.Column("signal_score", sa.Float(), nullable=True))
        batch_op.add_column(sa.Column("score_explanation", sa.String(length=255), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("signals") as batch_op:
        batch_op.drop_column("score_explanation")
        batch_op.drop_column("signal_score")

    with op.batch_alter_table("rolling_metrics") as batch_op:
        batch_op.drop_column("high_volatility")
        batch_op.drop_column("usage_shift")
        batch_op.drop_column("pace_proxy")
        batch_op.drop_column("opponent_rank")
        batch_op.drop_column("opponent_average_allowed")
        batch_op.drop_column("volatility_delta")
        batch_op.drop_column("volatility_index")
        batch_op.drop_column("trend_slope")
        batch_op.drop_column("recent_delta")
        batch_op.drop_column("ewma")
        batch_op.drop_column("season_z_score")
        batch_op.drop_column("season_rolling_stddev")
        batch_op.drop_column("season_rolling_avg")
        batch_op.drop_column("medium_z_score")
        batch_op.drop_column("medium_rolling_stddev")
        batch_op.drop_column("medium_rolling_avg")
        batch_op.drop_column("short_z_score")
        batch_op.drop_column("short_rolling_stddev")
        batch_op.drop_column("short_rolling_avg")
        batch_op.drop_column("season_values")
        batch_op.drop_column("medium_values")
        batch_op.drop_column("short_values")
        batch_op.drop_column("season_window_size")
        batch_op.drop_column("medium_window_size")
        batch_op.drop_column("short_window_size")
