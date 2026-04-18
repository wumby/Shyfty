from typing import Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.user_favorite import UserFavorite


def add_favorite(db: Session, user_id: int, signal_id: int) -> UserFavorite:
    existing = db.execute(
        select(UserFavorite).where(UserFavorite.user_id == user_id, UserFavorite.signal_id == signal_id)
    ).scalar_one_or_none()
    if existing:
        return existing
    fav = UserFavorite(user_id=user_id, signal_id=signal_id)
    db.add(fav)
    db.commit()
    return fav


def remove_favorite(db: Session, user_id: int, signal_id: int) -> None:
    db.execute(
        delete(UserFavorite).where(
            UserFavorite.user_id == user_id,
            UserFavorite.signal_id == signal_id,
        )
    )
    db.commit()


def get_favorited_signal_ids(db: Session, user_id: Optional[int], signal_ids: list[int]) -> set[int]:
    if not signal_ids or user_id is None:
        return set()
    rows = db.execute(
        select(UserFavorite.signal_id).where(
            UserFavorite.user_id == user_id,
            UserFavorite.signal_id.in_(signal_ids),
        )
    ).scalars().all()
    return set(rows)


def list_favorite_signal_ids(db: Session, user_id: int) -> list[int]:
    rows = db.execute(
        select(UserFavorite.signal_id)
        .where(UserFavorite.user_id == user_id)
        .order_by(UserFavorite.created_at.desc())
    ).scalars().all()
    return list(rows)
