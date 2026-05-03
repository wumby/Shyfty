"""Replace emoji reactions with Shyft-branded enum reactions.

Revision ID: 0018_shyft_reactions
Revises: 0017_expand_nfl_box_score_fields
Create Date: 2026-05-03 00:00:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy import inspect

revision = "0018_shyft_reactions"
down_revision = "0017_expand_nfl_box_score_fields"
branch_labels = None
depends_on = None


def _unique_constraint_names(table: str) -> set[str]:
    bind = op.get_bind()
    inspector = inspect(bind)
    return {uc["name"] for uc in inspector.get_unique_constraints(table) if uc.get("name")}


def upgrade() -> None:
    # Purge all existing reaction data — old emoji/legacy types are incompatible.
    op.execute("DELETE FROM signal_reactions")

    dialect = op.get_bind().dialect.name
    existing = _unique_constraint_names("signal_reactions")

    if dialect == "sqlite":
        # SQLite batch mode: recreate table to swap constraints without named drops.
        # The dev DB may already have the right constraint; skip if so.
        if "uq_user_signal_reaction" not in existing:
            with op.batch_alter_table("signal_reactions", recreate="always") as batch_op:
                batch_op.create_unique_constraint("uq_user_signal_reaction", ["user_id", "signal_id"])
    else:
        # PostgreSQL: drop old named constraint if present, then add new one.
        if "uq_user_signal_reaction_emoji" in existing:
            op.drop_constraint("uq_user_signal_reaction_emoji", "signal_reactions", type_="unique")
        if "uq_user_signal_reaction" not in existing:
            op.create_unique_constraint("uq_user_signal_reaction", "signal_reactions", ["user_id", "signal_id"])


def downgrade() -> None:
    dialect = op.get_bind().dialect.name
    existing = _unique_constraint_names("signal_reactions")

    if dialect == "sqlite":
        if "uq_user_signal_reaction" in existing:
            with op.batch_alter_table("signal_reactions", recreate="always") as batch_op:
                batch_op.drop_constraint("uq_user_signal_reaction", type_="unique")
                batch_op.create_unique_constraint(
                    "uq_user_signal_reaction_emoji", ["user_id", "signal_id", "type"]
                )
    else:
        if "uq_user_signal_reaction" in existing:
            op.drop_constraint("uq_user_signal_reaction", "signal_reactions", type_="unique")
        if "uq_user_signal_reaction_emoji" not in existing:
            op.create_unique_constraint(
                "uq_user_signal_reaction_emoji", "signal_reactions", ["user_id", "signal_id", "type"]
            )
