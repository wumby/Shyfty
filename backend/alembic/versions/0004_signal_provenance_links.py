"""add signal provenance links"""

from alembic import op
import sqlalchemy as sa

revision = "0004_signal_provenance_links"
down_revision = "0003_ingest_source_refs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("player_game_stats") as batch_op:
        batch_op.add_column(sa.Column("source_system", sa.String(length=32), nullable=True))
        batch_op.add_column(sa.Column("source_game_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("source_player_id", sa.String(length=64), nullable=True))
        batch_op.add_column(sa.Column("raw_snapshot_path", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("raw_payload_path", sa.String(length=255), nullable=True))
        batch_op.add_column(sa.Column("raw_record_index", sa.Integer(), nullable=True))

    with op.batch_alter_table("rolling_metrics") as batch_op:
        batch_op.add_column(sa.Column("source_stat_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_rolling_metrics_source_stat_id_player_game_stats",
            "player_game_stats",
            ["source_stat_id"],
            ["id"],
        )

    op.create_table(
        "rolling_metric_baseline_samples",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("rolling_metric_id", sa.Integer(), nullable=False),
        sa.Column("player_game_stat_id", sa.Integer(), nullable=False),
        sa.Column("sample_order", sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(["player_game_stat_id"], ["player_game_stats.id"]),
        sa.ForeignKeyConstraint(["rolling_metric_id"], ["rolling_metrics.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint(
            "rolling_metric_id",
            "player_game_stat_id",
            name="uq_rolling_metric_baseline_sample",
        ),
    )

    with op.batch_alter_table("signals") as batch_op:
        batch_op.add_column(sa.Column("rolling_metric_id", sa.Integer(), nullable=True))
        batch_op.add_column(sa.Column("source_stat_id", sa.Integer(), nullable=True))
        batch_op.create_foreign_key(
            "fk_signals_rolling_metric_id_rolling_metrics",
            "rolling_metrics",
            ["rolling_metric_id"],
            ["id"],
        )
        batch_op.create_foreign_key(
            "fk_signals_source_stat_id_player_game_stats",
            "player_game_stats",
            ["source_stat_id"],
            ["id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("signals") as batch_op:
        batch_op.drop_constraint("fk_signals_source_stat_id_player_game_stats", type_="foreignkey")
        batch_op.drop_constraint("fk_signals_rolling_metric_id_rolling_metrics", type_="foreignkey")
        batch_op.drop_column("source_stat_id")
        batch_op.drop_column("rolling_metric_id")

    op.drop_table("rolling_metric_baseline_samples")

    with op.batch_alter_table("rolling_metrics") as batch_op:
        batch_op.drop_constraint("fk_rolling_metrics_source_stat_id_player_game_stats", type_="foreignkey")
        batch_op.drop_column("source_stat_id")

    with op.batch_alter_table("player_game_stats") as batch_op:
        batch_op.drop_column("raw_record_index")
        batch_op.drop_column("raw_payload_path")
        batch_op.drop_column("raw_snapshot_path")
        batch_op.drop_column("source_player_id")
        batch_op.drop_column("source_game_id")
        batch_op.drop_column("source_system")
