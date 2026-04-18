"""add user_favorites table"""

from alembic import op
import sqlalchemy as sa

revision = "0007_favorites"
down_revision = "0006_comments"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "user_favorites",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("signal_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "signal_id", name="uq_user_signal_favorite"),
    )
    op.create_index(op.f("ix_user_favorites_signal_id"), "user_favorites", ["signal_id"], unique=False)
    op.create_index(op.f("ix_user_favorites_user_id"), "user_favorites", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_favorites_user_id"), table_name="user_favorites")
    op.drop_index(op.f("ix_user_favorites_signal_id"), table_name="user_favorites")
    op.drop_table("user_favorites")
