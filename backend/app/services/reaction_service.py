from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.signal import Signal
from app.models.signal_reaction import SignalReaction
from app.schemas.reaction import ReactionAggregateRead, ShyftReaction, SHYFT_REACTION_ORDER


def get_reaction_summaries(db: Session, signal_ids: list[int]) -> dict[int, list[ReactionAggregateRead]]:
    summaries: dict[int, list[ReactionAggregateRead]] = {signal_id: [] for signal_id in signal_ids}
    if not signal_ids:
        return summaries

    rows = db.execute(
        select(SignalReaction.signal_id, SignalReaction.type, func.count(SignalReaction.id))
        .where(SignalReaction.signal_id.in_(signal_ids))
        .group_by(SignalReaction.signal_id, SignalReaction.type)
    ).all()

    for signal_id, reaction_type, count in rows:
        try:
            shyft_type = ShyftReaction(reaction_type)
        except ValueError:
            continue
        summaries[signal_id].append(
            ReactionAggregateRead(type=shyft_type, count=int(count), reacted_by_current_user=False)
        )

    order = {r: i for i, r in enumerate(SHYFT_REACTION_ORDER)}
    for signal_id in summaries:
        summaries[signal_id].sort(key=lambda r: order.get(r.type, 99))

    return summaries


def get_user_reactions(db: Session, *, user_id: Optional[int], signal_ids: list[int]) -> dict[int, set[str]]:
    if user_id is None or not signal_ids:
        return {}
    rows = db.execute(
        select(SignalReaction.signal_id, SignalReaction.type).where(
            SignalReaction.user_id == user_id,
            SignalReaction.signal_id.in_(signal_ids),
        )
    ).all()
    result: dict[int, set[str]] = {}
    for signal_id, reaction_type in rows:
        result.setdefault(signal_id, set()).add(reaction_type)
    return result


def set_signal_reaction(
    db: Session,
    *,
    signal_id: int,
    user_id: int,
    reaction_type: str,
) -> SignalReaction:
    signal_exists = db.execute(select(Signal.id).where(Signal.id == signal_id)).scalar_one_or_none()
    if signal_exists is None:
        raise LookupError("Signal not found.")

    try:
        validated_type = ShyftReaction(reaction_type)
    except ValueError:
        raise ValueError(
            f"Invalid reaction type: {reaction_type!r}. Must be one of {[r.value for r in ShyftReaction]}."
        )

    existing = db.execute(
        select(SignalReaction).where(
            SignalReaction.signal_id == signal_id,
            SignalReaction.user_id == user_id,
        )
    ).scalars().all()
    for row in existing:
        db.delete(row)
    db.flush()

    reaction = SignalReaction(signal_id=signal_id, user_id=user_id, type=validated_type.value)
    db.add(reaction)
    db.commit()
    db.refresh(reaction)
    return reaction


def remove_signal_reaction(db: Session, *, signal_id: int, user_id: int) -> None:
    reactions = db.execute(
        select(SignalReaction).where(
            SignalReaction.signal_id == signal_id,
            SignalReaction.user_id == user_id,
        )
    ).scalars().all()
    for reaction in reactions:
        db.delete(reaction)
    if reactions:
        db.commit()
