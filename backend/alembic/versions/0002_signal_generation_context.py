"""add signal generation context keys"""

from alembic import op
import sqlalchemy as sa

revision = "0002_signal_generation_context"
down_revision = "0001_initial"
branch_labels = None
depends_on = None


def upgrade() -> None:
    bind = op.get_bind()

    with op.batch_alter_table("rolling_metrics") as batch_op:
        batch_op.add_column(sa.Column("game_id", sa.Integer(), nullable=True))
    with op.batch_alter_table("signals") as batch_op:
        batch_op.add_column(sa.Column("game_id", sa.Integer(), nullable=True))

    rolling_metrics = sa.table(
        "rolling_metrics",
        sa.column("player_id", sa.Integer()),
        sa.column("game_id", sa.Integer()),
    )
    signals = sa.table(
        "signals",
        sa.column("player_id", sa.Integer()),
        sa.column("game_id", sa.Integer()),
    )
    player_game_stats = sa.table(
        "player_game_stats",
        sa.column("player_id", sa.Integer()),
        sa.column("game_id", sa.Integer()),
    )

    latest_rolling_game_for_player = (
        sa.select(sa.func.max(player_game_stats.c.game_id))
        .where(player_game_stats.c.player_id == rolling_metrics.c.player_id)
        .scalar_subquery()
    )
    latest_signal_game_for_player = (
        sa.select(sa.func.max(player_game_stats.c.game_id))
        .where(player_game_stats.c.player_id == signals.c.player_id)
        .scalar_subquery()
    )

    bind.execute(rolling_metrics.update().values(game_id=latest_rolling_game_for_player))
    bind.execute(signals.update().values(game_id=latest_signal_game_for_player))

    with op.batch_alter_table("rolling_metrics") as batch_op:
        batch_op.alter_column("game_id", nullable=False)
        batch_op.drop_constraint("uq_player_metric", type_="unique")
        batch_op.create_foreign_key("fk_rolling_metrics_game_id_games", "games", ["game_id"], ["id"])
        batch_op.create_unique_constraint("uq_player_game_metric", ["player_id", "game_id", "metric_name"])

    with op.batch_alter_table("signals") as batch_op:
        batch_op.alter_column("game_id", nullable=False)
        batch_op.create_foreign_key("fk_signals_game_id_games", "games", ["game_id"], ["id"])
        batch_op.create_unique_constraint(
            "uq_signal_generation_context",
            ["player_id", "game_id", "metric_name", "signal_type"],
        )


def downgrade() -> None:
    with op.batch_alter_table("signals") as batch_op:
        batch_op.drop_constraint("uq_signal_generation_context", type_="unique")
        batch_op.drop_constraint("fk_signals_game_id_games", type_="foreignkey")
        batch_op.drop_column("game_id")

    with op.batch_alter_table("rolling_metrics") as batch_op:
        batch_op.drop_constraint("uq_player_game_metric", type_="unique")
        batch_op.drop_constraint("fk_rolling_metrics_game_id_games", type_="foreignkey")
        batch_op.create_unique_constraint("uq_player_metric", ["player_id", "metric_name"])
        batch_op.drop_column("game_id")
