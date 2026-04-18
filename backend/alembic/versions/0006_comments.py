"""add signal_comments table"""

from alembic import op
import sqlalchemy as sa

revision = "0006_comments"
down_revision = "0005_auth_and_reactions"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "signal_comments",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("signal_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_signal_comments_signal_id"), "signal_comments", ["signal_id"], unique=False)
    op.create_index(op.f("ix_signal_comments_user_id"), "signal_comments", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_signal_comments_user_id"), table_name="signal_comments")
    op.drop_index(op.f("ix_signal_comments_signal_id"), table_name="signal_comments")
    op.drop_table("signal_comments")
