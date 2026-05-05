from typing import Optional

from pydantic import BaseModel


class ProfilePreferencesRead(BaseModel):
    preferred_league: Optional[str] = None
    preferred_shyft_type: Optional[str] = None
    default_sort_mode: str = "newest"
    default_feed_mode: str = "all"
    notification_releases: bool = False
    notification_digest: bool = False


class ProfilePreferencesUpdate(BaseModel):
    preferred_league: Optional[str] = None
    preferred_shyft_type: Optional[str] = None
    default_sort_mode: Optional[str] = None
    default_feed_mode: Optional[str] = None
    notification_releases: Optional[bool] = None
    notification_digest: Optional[bool] = None


class FollowSummaryRead(BaseModel):
    players: list[int]
    teams: list[int]


class UserProfileRead(BaseModel):
    display_name: Optional[str] = None
    preferences: ProfilePreferencesRead
    follows: FollowSummaryRead


class UserProfileUpdate(BaseModel):
    display_name: Optional[str] = None
