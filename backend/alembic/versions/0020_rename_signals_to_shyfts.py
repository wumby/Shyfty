"""rename signals tables and columns to shyfts

Revision ID: 0020_rename_signals_to_shyfts
Revises: 0019_schedule_first_sync
Create Date: 2026-05-04
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import text

revision = "0020_rename_signals_to_shyfts"
down_revision = "0019_schedule_first_sync"
branch_labels = None
depends_on = None


def upgrade() -> None:
    conn = op.get_bind()

    # Rename columns in signals table via batch (SQLite requires full table recreate)
    with op.batch_alter_table("signals", recreate="always") as batch_op:
        batch_op.alter_column("signal_type", new_column_name="shyft_type")
        batch_op.alter_column("signal_score", new_column_name="shyft_score")

    op.rename_table("signals", "shyfts")

    # signal_reactions: rename signal_id column, then rename table
    # Use raw SQL to avoid FK reflection issues after signals was renamed
    op.create_table(
        "shyft_reactions_new",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("shyft_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["shyft_id"], ["shyfts.id"]),
    )
    conn.execute(text(
        "INSERT INTO shyft_reactions_new (id, user_id, shyft_id, type, created_at, updated_at) "
        "SELECT id, user_id, signal_id, type, created_at, updated_at FROM signal_reactions"
    ))
    conn.execute(text("DROP TABLE signal_reactions"))
    conn.execute(text("ALTER TABLE shyft_reactions_new RENAME TO shyft_reactions"))

    # signal_comments: rename signal_id column, then rename table
    op.create_table(
        "shyft_comments_new",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("shyft_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["shyft_id"], ["shyfts.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    conn.execute(text(
        "INSERT INTO shyft_comments_new (id, shyft_id, user_id, body, created_at, updated_at) "
        "SELECT id, signal_id, user_id, body, created_at, updated_at FROM signal_comments"
    ))
    op.create_table(
        "comment_reports_new",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("comment_id", sa.Integer(), nullable=False),
        sa.Column("reporter_user_id", sa.Integer(), nullable=False),
        sa.Column("reason", sa.String(length=48), nullable=False),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("status", sa.String(length=24), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["comment_id"], ["shyft_comments_new.id"]),
        sa.ForeignKeyConstraint(["reporter_user_id"], ["users.id"]),
        sa.UniqueConstraint("comment_id", "reporter_user_id", name="uq_comment_reporter"),
    )
    conn.execute(text(
        "INSERT INTO comment_reports_new (id, comment_id, reporter_user_id, reason, notes, status, created_at) "
        "SELECT id, comment_id, reporter_user_id, reason, notes, status, created_at FROM comment_reports"
    ))
    conn.execute(text("DROP TABLE comment_reports"))
    conn.execute(text("DROP TABLE signal_comments"))
    conn.execute(text("ALTER TABLE shyft_comments_new RENAME TO shyft_comments"))
    conn.execute(text("ALTER TABLE comment_reports_new RENAME TO comment_reports"))
    op.create_index(op.f("ix_comment_reports_comment_id"), "comment_reports", ["comment_id"], unique=False)
    op.create_index(op.f("ix_comment_reports_reporter_user_id"), "comment_reports", ["reporter_user_id"], unique=False)

    # user_preferences: rename preferred_signal_type
    with op.batch_alter_table("user_preferences", recreate="always") as batch_op:
        batch_op.alter_column("preferred_signal_type", new_column_name="preferred_shyft_type")

    # ingest_runs: rename signals_created/signals_updated
    with op.batch_alter_table("ingest_runs", recreate="always") as batch_op:
        batch_op.alter_column("signals_created", new_column_name="shyfts_created")
        batch_op.alter_column("signals_updated", new_column_name="shyfts_updated")


def downgrade() -> None:
    conn = op.get_bind()

    with op.batch_alter_table("ingest_runs", recreate="always") as batch_op:
        batch_op.alter_column("shyfts_created", new_column_name="signals_created")
        batch_op.alter_column("shyfts_updated", new_column_name="signals_updated")

    with op.batch_alter_table("user_preferences", recreate="always") as batch_op:
        batch_op.alter_column("preferred_shyft_type", new_column_name="preferred_signal_type")

    op.create_table(
        "signal_comments_new",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("signal_id", sa.Integer(), nullable=False),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("body", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"]),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
    )
    conn.execute(text(
        "INSERT INTO signal_comments_new (id, signal_id, user_id, body, created_at, updated_at) "
        "SELECT id, shyft_id, user_id, body, created_at, updated_at FROM shyft_comments"
    ))
    conn.execute(text("DROP TABLE shyft_comments"))
    conn.execute(text("ALTER TABLE signal_comments_new RENAME TO signal_comments"))

    op.create_table(
        "signal_reactions_new",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("user_id", sa.Integer(), nullable=False),
        sa.Column("signal_id", sa.Integer(), nullable=False),
        sa.Column("type", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(), nullable=False),
        sa.Column("updated_at", sa.DateTime(), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.ForeignKeyConstraint(["signal_id"], ["signals.id"]),
    )
    conn.execute(text(
        "INSERT INTO signal_reactions_new (id, user_id, signal_id, type, created_at, updated_at) "
        "SELECT id, user_id, shyft_id, type, created_at, updated_at FROM shyft_reactions"
    ))
    conn.execute(text("DROP TABLE shyft_reactions"))
    conn.execute(text("ALTER TABLE signal_reactions_new RENAME TO signal_reactions"))

    op.rename_table("shyfts", "signals")
    with op.batch_alter_table("signals", recreate="always") as batch_op:
        batch_op.alter_column("shyft_score", new_column_name="signal_score")
        batch_op.alter_column("shyft_type", new_column_name="signal_type")
