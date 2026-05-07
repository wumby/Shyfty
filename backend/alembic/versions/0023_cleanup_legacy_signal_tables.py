"""cleanup legacy signal tables

Revision ID: 0023_cleanup_legacy_signal_tables
Revises: 0022_password_reset_tokens
Create Date: 2026-05-06
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect, text

revision = "0023_cleanup_legacy_signal_tables"
down_revision = "0022_password_reset_tokens"
branch_labels = None
depends_on = None


def _tables() -> set[str]:
    return set(inspect(op.get_bind()).get_table_names())


def upgrade() -> None:
    tables = _tables()

    if "comment_reports" in tables:
        op.create_table(
            "comment_reports_new",
            sa.Column("id", sa.Integer(), primary_key=True),
            sa.Column("comment_id", sa.Integer(), nullable=False),
            sa.Column("reporter_user_id", sa.Integer(), nullable=False),
            sa.Column("reason", sa.String(length=48), nullable=False),
            sa.Column("notes", sa.Text(), nullable=True),
            sa.Column("status", sa.String(length=24), nullable=False),
            sa.Column("created_at", sa.DateTime(), nullable=False),
            sa.ForeignKeyConstraint(["comment_id"], ["shyft_comments.id"]),
            sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"]),
            sa.UniqueConstraint("comment_id", "reporter_user_id", name="uq_comment_reporter"),
        )
        op.execute(
            text(
                "INSERT INTO comment_reports_new "
                "(id, comment_id, reporter_user_id, reason, notes, status, created_at) "
                "SELECT id, comment_id, reporter_user_id, reason, notes, status, created_at "
                "FROM comment_reports"
            )
        )
        op.execute(text("DROP TABLE comment_reports"))
        op.execute(text("ALTER TABLE comment_reports_new RENAME TO comment_reports"))
        op.create_index(op.f("ix_comment_reports_comment_id"), "comment_reports", ["comment_id"], unique=False)
        op.create_index(op.f("ix_comment_reports_reporter_user_id"), "comment_reports", ["reporter_user_id"], unique=False)

    if "user_favorites" in tables:
        op.execute(text("DROP TABLE user_favorites"))
    if "user_saved_views" in tables:
        op.execute(text("DROP TABLE user_saved_views"))


def downgrade() -> None:
    # These legacy tables are intentionally not restored. They are not part of the
    # current runtime model and referenced the retired signals table.
    pass
