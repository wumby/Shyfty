from typing import Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.signal import Signal
from app.models.signal_reaction import SignalReaction
from app.schemas.reaction import ReactionAggregateRead


LEGACY_TO_EMOJI = {
    "agree": "👍",
    "strong": "🔥",
    "risky": "👎",
}
MAX_REACTIONS_PER_USER_PER_SIGNAL = 6


class ReactionLimitError(ValueError):
    pass


def normalize_emoji(raw: str) -> str:
    value = (raw or "").strip()
    if not value:
        raise ValueError("Emoji is required.")
    return LEGACY_TO_EMOJI.get(value.lower(), value)


def get_reaction_summaries(db: Session, signal_ids: list[int]) -> dict[int, list[ReactionAggregateRead]]:
    summaries = {signal_id: [] for signal_id in signal_ids}
    if not signal_ids:
        return summaries

    rows = db.execute(
        select(SignalReaction.signal_id, SignalReaction.type, func.count(SignalReaction.id))
        .where(SignalReaction.signal_id.in_(signal_ids))
        .group_by(SignalReaction.signal_id, SignalReaction.type)
        .order_by(SignalReaction.signal_id.asc(), func.count(SignalReaction.id).desc())
    ).all()

    for signal_id, emoji, count in rows:
        summaries.setdefault(signal_id, []).append(
            ReactionAggregateRead(emoji=emoji, count=int(count), reacted_by_current_user=False)
        )
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
    for signal_id, emoji in rows:
        result.setdefault(signal_id, set()).add(emoji)
    return result


def set_signal_reaction(
    db: Session,
    *,
    signal_id: int,
    user_id: int,
    emoji: Optional[str] = None,
    reaction_type: Optional[str] = None,
) -> SignalReaction:
    signal_exists = db.execute(select(Signal.id).where(Signal.id == signal_id)).scalar_one_or_none()
    if signal_exists is None:
        raise LookupError("Signal not found.")

    is_legacy_single_choice = emoji is None and reaction_type is not None
    normalized = normalize_emoji(emoji or reaction_type or "")
    removed_other_reactions = False

    if is_legacy_single_choice:
        existing_rows = db.execute(
            select(SignalReaction).where(
                SignalReaction.signal_id == signal_id,
                SignalReaction.user_id == user_id,
            )
        ).scalars().all()
        for existing in existing_rows:
            if existing.type != normalized:
                db.delete(existing)
                removed_other_reactions = True
        db.flush()

    reaction = db.execute(
        select(SignalReaction).where(
            SignalReaction.signal_id == signal_id,
            SignalReaction.user_id == user_id,
            SignalReaction.type == normalized,
        )
    ).scalar_one_or_none()
    if reaction is None:
        own_count = db.execute(
            select(func.count(SignalReaction.id)).where(
                SignalReaction.signal_id == signal_id,
                SignalReaction.user_id == user_id,
            )
        ).scalar_one()
        if own_count >= MAX_REACTIONS_PER_USER_PER_SIGNAL:
            raise ReactionLimitError(f"Reaction limit reached ({MAX_REACTIONS_PER_USER_PER_SIGNAL} per signal).")
        reaction = SignalReaction(signal_id=signal_id, user_id=user_id, type=normalized)
        db.add(reaction)
        db.commit()
        db.refresh(reaction)
    elif removed_other_reactions:
        db.commit()
    return reaction


def remove_signal_reaction(db: Session, *, signal_id: int, user_id: int, emoji: Optional[str] = None) -> None:
    if emoji is None:
        reactions = db.execute(
            select(SignalReaction).where(
                SignalReaction.signal_id == signal_id,
                SignalReaction.user_id == user_id,
            )
        ).scalars().all()
        if not reactions:
            return
        for reaction in reactions:
            db.delete(reaction)
        db.commit()
        return

    normalized = normalize_emoji(emoji)
    reaction = db.execute(
        select(SignalReaction).where(
            SignalReaction.signal_id == signal_id,
            SignalReaction.user_id == user_id,
            SignalReaction.type == normalized,
        )
    ).scalar_one_or_none()
    if reaction is None:
        return
    db.delete(reaction)
    db.commit()
