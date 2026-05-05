from datetime import datetime
from enum import Enum

from pydantic import BaseModel


class ShyftReaction(str, Enum):
    SHYFT_UP = "SHYFT_UP"
    SHYFT_DOWN = "SHYFT_DOWN"
    SHYFT_EYE = "SHYFT_EYE"


SHYFT_REACTION_ORDER = [ShyftReaction.SHYFT_UP, ShyftReaction.SHYFT_DOWN, ShyftReaction.SHYFT_EYE]

ReactionType = str


class ReactionWrite(BaseModel):
    type: ShyftReaction


class ReactionAggregateRead(BaseModel):
    type: ShyftReaction
    count: int
    reacted_by_current_user: bool = False


class ReactionSummaryRead(BaseModel):
    shyft_up: int = 0
    shyft_down: int = 0
    shyft_eye: int = 0


class ReactionRead(BaseModel):
    id: int
    shyft_id: int
    user_id: int
    type: ShyftReaction
    created_at: datetime
    updated_at: datetime
