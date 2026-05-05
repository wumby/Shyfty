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
    conn.execute(text(
        "CREATE TABLE shyft_reactions_new ("
        "id INTEGER NOT NULL PRIMARY KEY, "
        "user_id INTEGER NOT NULL, "
        "shyft_id INTEGER NOT NULL, "
        "type VARCHAR(16) NOT NULL, "
        "created_at DATETIME NOT NULL, "
        "updated_at DATETIME NOT NULL, "
        "FOREIGN KEY(user_id) REFERENCES users(id), "
        "FOREIGN KEY(shyft_id) REFERENCES shyfts(id)"
        ")"
    ))
    conn.execute(text(
        "INSERT INTO shyft_reactions_new (id, user_id, shyft_id, type, created_at, updated_at) "
        "SELECT id, user_id, signal_id, type, created_at, updated_at FROM signal_reactions"
    ))
    conn.execute(text("DROP TABLE signal_reactions"))
    conn.execute(text("ALTER TABLE shyft_reactions_new RENAME TO shyft_reactions"))

    # signal_comments: rename signal_id column, then rename table
    conn.execute(text(
        "CREATE TABLE shyft_comments_new ("
        "id INTEGER NOT NULL PRIMARY KEY, "
        "shyft_id INTEGER NOT NULL, "
        "user_id INTEGER NOT NULL, "
        "body TEXT NOT NULL, "
        "created_at DATETIME NOT NULL, "
        "updated_at DATETIME NOT NULL, "
        "FOREIGN KEY(shyft_id) REFERENCES shyfts(id), "
        "FOREIGN KEY(user_id) REFERENCES users(id)"
        ")"
    ))
    conn.execute(text(
        "INSERT INTO shyft_comments_new (id, shyft_id, user_id, body, created_at, updated_at) "
        "SELECT id, signal_id, user_id, body, created_at, updated_at FROM signal_comments"
    ))
    conn.execute(text("DROP TABLE signal_comments"))
    conn.execute(text("ALTER TABLE shyft_comments_new RENAME TO shyft_comments"))

    # Update comment_reports FK (still points to signal_comments id, now shyft_comments)
    # The id column is the same, just table name changed — no data migration needed

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

    conn.execute(text(
        "CREATE TABLE signal_comments_new ("
        "id INTEGER NOT NULL PRIMARY KEY, "
        "signal_id INTEGER NOT NULL, "
        "user_id INTEGER NOT NULL, "
        "body TEXT NOT NULL, "
        "created_at DATETIME NOT NULL, "
        "updated_at DATETIME NOT NULL, "
        "FOREIGN KEY(signal_id) REFERENCES signals(id), "
        "FOREIGN KEY(user_id) REFERENCES users(id)"
        ")"
    ))
    conn.execute(text(
        "INSERT INTO signal_comments_new (id, signal_id, user_id, body, created_at, updated_at) "
        "SELECT id, shyft_id, user_id, body, created_at, updated_at FROM shyft_comments"
    ))
    conn.execute(text("DROP TABLE shyft_comments"))
    conn.execute(text("ALTER TABLE signal_comments_new RENAME TO signal_comments"))

    conn.execute(text(
        "CREATE TABLE signal_reactions_new ("
        "id INTEGER NOT NULL PRIMARY KEY, "
        "user_id INTEGER NOT NULL, "
        "signal_id INTEGER NOT NULL, "
        "type VARCHAR(16) NOT NULL, "
        "created_at DATETIME NOT NULL, "
        "updated_at DATETIME NOT NULL, "
        "FOREIGN KEY(user_id) REFERENCES users(id), "
        "FOREIGN KEY(signal_id) REFERENCES signals(id)"
        ")"
    ))
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
