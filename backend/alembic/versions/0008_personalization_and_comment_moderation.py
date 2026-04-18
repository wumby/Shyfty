"""add personalization and comment moderation tables"""

from alembic import op
import sqlalchemy as sa

revision = "0008_personalization_and_comment_moderation"
down_revision = "0007_favorites"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("signal_comments", sa.Column("updated_at", sa.DateTime(), nullable=False, server_default=sa.func.now()))

    op.create_table(
        "comment_reports",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("comment_id", sa.Integer(), nullable=False),
        sa.Column("reporter_user_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=48), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["comment_id"], ["signal_comments.id"]),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("comment_id", "reporter_user_id", name="uq_comment_reporter"),
    )
    op.create_index(op.f("ix_comment_reports_comment_id"), "comment_reports", ["comment_id"], unique=False)
    op.create_index(op.f("ix_comment_reports_reporter_user_id"), "comment_reports", ["reporter_user_id"], unique=False)

    op.create_table(
        "user_follows",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("entity_type", sa.String(length=16), nullable=False),
        sa.Column("entity_id", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "entity_type", "entity_id", name="uq_user_follow_entity"),
    )
    op.create_index(op.f("ix_user_follows_user_id"), "user_follows", ["user_id"], unique=False)
    op.create_index(op.f("ix_user_follows_entity_type"), "user_follows", ["entity_type"], unique=False)
    op.create_index(op.f("ix_user_follows_entity_id"), "user_follows", ["entity_id"], unique=False)

    op.create_table(
        "user_preferences",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("preferred_league", sa.String(length=16), nullable=True),
        sa.Column("preferred_signal_type", sa.String(length=32), nullable=True),
        sa.Column("default_sort_mode", sa.String(length=32), nullable=False),
        sa.Column("default_feed_mode", sa.String(length=32), nullable=False),
        sa.Column("notification_releases", sa.Boolean(), nullable=False),
        sa.Column("notification_digest", sa.Boolean(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id"),
    )
    op.create_index(op.f("ix_user_preferences_user_id"), "user_preferences", ["user_id"], unique=True)

    op.create_table(
        "user_saved_views",
        sa.Column("id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("name", sa.String(length=80), nullable=False),
        sa.Column("league", sa.String(length=16), nullable=True),
        sa.Column("signal_type", sa.String(length=32), nullable=True),
        sa.Column("player", sa.String(length=120), nullable=True),
        sa.Column("sort_mode", sa.String(length=32), nullable=False),
        sa.Column("feed_mode", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_user_saved_views_user_id"), "user_saved_views", ["user_id"], unique=False)


def downgrade() -> None:
    op.drop_index(op.f("ix_user_saved_views_user_id"), table_name="user_saved_views")
    op.drop_table("user_saved_views")

    op.drop_index(op.f("ix_user_preferences_user_id"), table_name="user_preferences")
    op.drop_table("user_preferences")

    op.drop_index(op.f("ix_user_follows_entity_id"), table_name="user_follows")
    op.drop_index(op.f("ix_user_follows_entity_type"), table_name="user_follows")
    op.drop_index(op.f("ix_user_follows_user_id"), table_name="user_follows")
    op.drop_table("user_follows")

    op.drop_index(op.f("ix_comment_reports_reporter_user_id"), table_name="comment_reports")
    op.drop_index(op.f("ix_comment_reports_comment_id"), table_name="comment_reports")
    op.drop_table("comment_reports")

    op.drop_column("signal_comments", "updated_at")
