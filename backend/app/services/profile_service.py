from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.user_follow import UserFollow
from app.models.user_preference import UserPreference
from app.schemas.profile import (
    FollowSummaryRead,
    ProfilePreferencesRead,
    ProfilePreferencesUpdate,
    UserProfileRead,
)


def _get_or_create_preferences(db: Session, user_id: int) -> UserPreference:
    prefs = db.execute(select(UserPreference).where(UserPreference.user_id == user_id)).scalar_one_or_none()
    if prefs is None:
        prefs = UserPreference(user_id=user_id)
        db.add(prefs)
        db.commit()
        db.refresh(prefs)
    return prefs


def get_profile(db: Session, user_id: int) -> UserProfileRead:
    prefs = _get_or_create_preferences(db, user_id)
    follows = db.execute(select(UserFollow).where(UserFollow.user_id == user_id)).scalars().all()
    return UserProfileRead(
        preferences=ProfilePreferencesRead(
            preferred_league=prefs.preferred_league,
            preferred_signal_type=prefs.preferred_signal_type,
            default_sort_mode=prefs.default_sort_mode,
            default_feed_mode=prefs.default_feed_mode,
            notification_releases=prefs.notification_releases,
            notification_digest=prefs.notification_digest,
        ),
        follows=FollowSummaryRead(
            players=[follow.entity_id for follow in follows if follow.entity_type == "player"],
            teams=[follow.entity_id for follow in follows if follow.entity_type == "team"],
        ),
    )


def update_preferences(db: Session, user_id: int, payload: ProfilePreferencesUpdate) -> ProfilePreferencesRead:
    prefs = _get_or_create_preferences(db, user_id)
    for field, value in payload.model_dump(exclude_unset=True).items():
        setattr(prefs, field, value)
    db.add(prefs)
    db.commit()
    db.refresh(prefs)
    return ProfilePreferencesRead(
        preferred_league=prefs.preferred_league,
        preferred_signal_type=prefs.preferred_signal_type,
        default_sort_mode=prefs.default_sort_mode,
        default_feed_mode=prefs.default_feed_mode,
        notification_releases=prefs.notification_releases,
        notification_digest=prefs.notification_digest,
    )


def set_follow(db: Session, user_id: int, entity_type: str, entity_id: int) -> None:
    existing = db.execute(
        select(UserFollow).where(
            UserFollow.user_id == user_id,
            UserFollow.entity_type == entity_type,
            UserFollow.entity_id == entity_id,
        )
    ).scalar_one_or_none()
    if existing is not None:
        return
    db.add(UserFollow(user_id=user_id, entity_type=entity_type, entity_id=entity_id))
    db.commit()


def remove_follow(db: Session, user_id: int, entity_type: str, entity_id: int) -> None:
    db.execute(
        delete(UserFollow).where(
            UserFollow.user_id == user_id,
            UserFollow.entity_type == entity_type,
            UserFollow.entity_id == entity_id,
        )
    )
    db.commit()

