from typing import Optional

from fastapi import APIRouter, Depends, HTTPException, Response, status
from sqlalchemy.orm import Session

from app.api.dependencies import get_current_user, get_db
from app.models.user import User
from app.schemas.profile import (
    ProfilePreferencesRead,
    ProfilePreferencesUpdate,
    SavedViewCreate,
    SavedViewRead,
    UserProfileRead,
)
from app.services.profile_service import (
    add_saved_view,
    delete_saved_view,
    get_profile,
    remove_follow,
    set_follow,
    update_preferences,
)

router = APIRouter()


def _require_user(user: Optional[User]) -> User:
    if user is None:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Authentication required.")
    return user


@router.get("/profile", response_model=UserProfileRead)
def get_profile_route(
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> UserProfileRead:
    user = _require_user(current_user)
    return get_profile(db, user.id)


@router.put("/profile/preferences", response_model=ProfilePreferencesRead)
def update_preferences_route(
    payload: ProfilePreferencesUpdate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> ProfilePreferencesRead:
    user = _require_user(current_user)
    return update_preferences(db, user.id, payload)


@router.post("/profile/saved-views", response_model=SavedViewRead, status_code=status.HTTP_201_CREATED)
def create_saved_view(
    payload: SavedViewCreate,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> SavedViewRead:
    user = _require_user(current_user)
    return add_saved_view(db, user.id, payload)


@router.delete("/profile/saved-views/{saved_view_id}", status_code=status.HTTP_204_NO_CONTENT)
def remove_saved_view(
    saved_view_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> Response:
    user = _require_user(current_user)
    delete_saved_view(db, user.id, saved_view_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/players/{player_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
def follow_player(
    player_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> Response:
    user = _require_user(current_user)
    set_follow(db, user.id, "player", player_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/players/{player_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
def unfollow_player(
    player_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> Response:
    user = _require_user(current_user)
    remove_follow(db, user.id, "player", player_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.post("/teams/{team_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
def follow_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> Response:
    user = _require_user(current_user)
    set_follow(db, user.id, "team", team_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)


@router.delete("/teams/{team_id}/follow", status_code=status.HTTP_204_NO_CONTENT)
def unfollow_team(
    team_id: int,
    db: Session = Depends(get_db),
    current_user: Optional[User] = Depends(get_current_user),
) -> Response:
    user = _require_user(current_user)
    remove_follow(db, user.id, "team", team_id)
    return Response(status_code=status.HTTP_204_NO_CONTENT)
