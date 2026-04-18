from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.signal import Signal
from app.models.signal_reaction import SignalReaction
from app.schemas.reaction import ReactionSummaryRead, ReactionType


def get_reaction_summaries(db: Session, signal_ids: list[int]) -> dict[int, ReactionSummaryRead]:
    summaries = {signal_id: ReactionSummaryRead() for signal_id in signal_ids}
    if not signal_ids:
        return summaries

    rows = db.execute(
        select(SignalReaction.signal_id, SignalReaction.type, func.count(SignalReaction.id))
        .where(SignalReaction.signal_id.in_(signal_ids))
        .group_by(SignalReaction.signal_id, SignalReaction.type)
    ).all()

    for signal_id, reaction_type, count in rows:
        summary = summaries.setdefault(signal_id, ReactionSummaryRead())
        setattr(summary, reaction_type, count)
    return summaries


def get_user_reactions(db: Session, *, user_id: Optional[int], signal_ids: list[int]) -> dict[int, ReactionType]:
    if user_id is None or not signal_ids:
        return {}
    rows = db.execute(
        select(SignalReaction.signal_id, SignalReaction.type).where(
            SignalReaction.user_id == user_id,
            SignalReaction.signal_id.in_(signal_ids),
        )
    ).all()
    return {signal_id: reaction_type for signal_id, reaction_type in rows}


def set_signal_reaction(
    db: Session,
    *,
    signal_id: int,
    user_id: int,
    reaction_type: ReactionType,
) -> SignalReaction:
    signal_exists = db.execute(select(Signal.id).where(Signal.id == signal_id)).scalar_one_or_none()
    if signal_exists is None:
        raise LookupError("Signal not found.")

    reaction = db.execute(
        select(SignalReaction).where(SignalReaction.signal_id == signal_id, SignalReaction.user_id == user_id)
    ).scalar_one_or_none()
    if reaction is None:
        reaction = SignalReaction(signal_id=signal_id, user_id=user_id, type=reaction_type)
        db.add(reaction)
    else:
        reaction.type = reaction_type

    db.commit()
    db.refresh(reaction)
    return reaction


def remove_signal_reaction(db: Session, *, signal_id: int, user_id: int) -> None:
    reaction = db.execute(
        select(SignalReaction).where(SignalReaction.signal_id == signal_id, SignalReaction.user_id == user_id)
    ).scalar_one_or_none()
    if reaction is None:
        return
    db.delete(reaction)
    db.commit()
