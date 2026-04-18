from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class SavedViewRead(BaseModel):
    id: int
    name: str
    league: Optional[str] = None
    signal_type: Optional[str] = None
    player: Optional[str] = None
    sort_mode: str
    feed_mode: str
    created_at: datetime
    updated_at: datetime


class SavedViewCreate(BaseModel):
    name: str = Field(..., min_length=1, max_length=80)
    league: Optional[str] = None
    signal_type: Optional[str] = None
    player: Optional[str] = Field(default=None, max_length=120)
    sort_mode: str = Field(default="newest", min_length=3, max_length=32)
    feed_mode: str = Field(default="all", min_length=3, max_length=32)


class ProfilePreferencesRead(BaseModel):
    preferred_league: Optional[str] = None
    preferred_signal_type: Optional[str] = None
    default_sort_mode: str = "newest"
    default_feed_mode: str = "all"
    notification_releases: bool = False
    notification_digest: bool = False


class ProfilePreferencesUpdate(BaseModel):
    preferred_league: Optional[str] = None
    preferred_signal_type: Optional[str] = None
    default_sort_mode: Optional[str] = None
    default_feed_mode: Optional[str] = None
    notification_releases: Optional[bool] = None
    notification_digest: Optional[bool] = None


class FollowSummaryRead(BaseModel):
    players: list[int]
    teams: list[int]


class UserProfileRead(BaseModel):
    preferences: ProfilePreferencesRead
    follows: FollowSummaryRead
    saved_views: list[SavedViewRead]
