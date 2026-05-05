"""add display_name to users

Revision ID: 0021_add_user_display_name
Revises: 0020_rename_signals_to_shyfts
Create Date: 2026-05-05
"""

from alembic import op
import sqlalchemy as sa

revision = "0021_add_user_display_name"
down_revision = "0020_rename_signals_to_shyfts"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("users", recreate="always") as batch_op:
        batch_op.add_column(sa.Column("display_name", sa.String(length=80), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("users", recreate="always") as batch_op:
        batch_op.drop_column("display_name")
