from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.shyft import Shyft
from app.models.shyft_reaction import ShyftReactionRecord
from app.schemas.reaction import ReactionAggregateRead, ShyftReaction, SHYFT_REACTION_ORDER


def get_reaction_summaries(db: Session, shyft_ids: list[int]) -> dict[int, list[ReactionAggregateRead]]:
    summaries: dict[int, list[ReactionAggregateRead]] = {shyft_id: [] for shyft_id in shyft_ids}
    if not shyft_ids:
        return summaries

    rows = db.execute(
        select(ShyftReactionRecord.shyft_id, ShyftReactionRecord.type, func.count(ShyftReactionRecord.id))
        .where(ShyftReactionRecord.shyft_id.in_(shyft_ids))
        .group_by(ShyftReactionRecord.shyft_id, ShyftReactionRecord.type)
    ).all()

    for shyft_id, reaction_type, count in rows:
        try:
            shyft_type = ShyftReaction(reaction_type)
        except ValueError:
            continue
        summaries[shyft_id].append(
            ReactionAggregateRead(type=shyft_type, count=int(count), reacted_by_current_user=False)
        )

    order = {r: i for i, r in enumerate(SHYFT_REACTION_ORDER)}
    for shyft_id in summaries:
        summaries[shyft_id].sort(key=lambda r: order.get(r.type, 99))

    return summaries


def get_user_reactions(db: Session, *, user_id: Optional[int], shyft_ids: list[int]) -> dict[int, set[str]]:
    if user_id is None or not shyft_ids:
        return {}
    rows = db.execute(
        select(ShyftReactionRecord.shyft_id, ShyftReactionRecord.type).where(
            ShyftReactionRecord.user_id == user_id,
            ShyftReactionRecord.shyft_id.in_(shyft_ids),
        )
    ).all()
    result: dict[int, set[str]] = {}
    for shyft_id, reaction_type in rows:
        result.setdefault(shyft_id, set()).add(reaction_type)
    return result


def set_shyft_reaction(
    db: Session,
    *,
    shyft_id: int,
    user_id: int,
    reaction_type: str,
) -> ShyftReactionRecord:
    signal_exists = db.execute(select(Shyft.id).where(Shyft.id == shyft_id)).scalar_one_or_none()
    if signal_exists is None:
        raise LookupError("Shyft not found.")

    try:
        validated_type = ShyftReaction(reaction_type)
    except ValueError:
        raise ValueError(
            f"Invalid reaction type: {reaction_type!r}. Must be one of {[r.value for r in ShyftReaction]}."
        )

    existing = db.execute(
        select(ShyftReactionRecord).where(
            ShyftReactionRecord.shyft_id == shyft_id,
            ShyftReactionRecord.user_id == user_id,
        )
    ).scalars().all()
    for row in existing:
        db.delete(row)
    db.flush()

    reaction = ShyftReactionRecord(shyft_id=shyft_id, user_id=user_id, type=validated_type.value)
    db.add(reaction)
    db.commit()
    db.refresh(reaction)
    return reaction


def remove_shyft_reaction(db: Session, *, shyft_id: int, user_id: int) -> None:
    reactions = db.execute(
        select(ShyftReactionRecord).where(
            ShyftReactionRecord.shyft_id == shyft_id,
            ShyftReactionRecord.user_id == user_id,
        )
    ).scalars().all()
    for reaction in reactions:
        db.delete(reaction)
    if reactions:
        db.commit()
