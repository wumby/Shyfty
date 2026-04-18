from __future__ import annotations

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.user_follow import UserFollow
from app.models.user_preference import UserPreference
from app.models.user_saved_view import UserSavedView
from app.schemas.profile import (
    FollowSummaryRead,
    ProfilePreferencesRead,
    ProfilePreferencesUpdate,
    SavedViewCreate,
    SavedViewRead,
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


def _saved_view_read(view: UserSavedView) -> SavedViewRead:
    return SavedViewRead(
        id=view.id,
        name=view.name,
        league=view.league,
        signal_type=view.signal_type,
        player=view.player,
        sort_mode=view.sort_mode,
        feed_mode=view.feed_mode,
        created_at=view.created_at,
        updated_at=view.updated_at,
    )


def get_profile(db: Session, user_id: int) -> UserProfileRead:
    prefs = _get_or_create_preferences(db, user_id)
    follows = db.execute(select(UserFollow).where(UserFollow.user_id == user_id)).scalars().all()
    saved_views = db.execute(
        select(UserSavedView).where(UserSavedView.user_id == user_id).order_by(UserSavedView.updated_at.desc())
    ).scalars().all()
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
        saved_views=[_saved_view_read(view) for view in saved_views],
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


def add_saved_view(db: Session, user_id: int, payload: SavedViewCreate) -> SavedViewRead:
    view = UserSavedView(user_id=user_id, **payload.model_dump())
    db.add(view)
    db.commit()
    db.refresh(view)
    return _saved_view_read(view)


def delete_saved_view(db: Session, user_id: int, saved_view_id: int) -> None:
    db.execute(
        delete(UserSavedView).where(UserSavedView.user_id == user_id, UserSavedView.id == saved_view_id)
    )
    db.commit()
