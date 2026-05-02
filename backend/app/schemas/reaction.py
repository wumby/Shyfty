from datetime import datetime

from pydantic import BaseModel


ReactionType = str


class ReactionWrite(BaseModel):
    type: str = "agree"


class EmojiReactionWrite(BaseModel):
    emoji: str


class ReactionAggregateRead(BaseModel):
    emoji: str
    count: int
    reacted_by_current_user: bool = False


class ReactionSummaryRead(BaseModel):
    strong: int = 0
    agree: int = 0
    risky: int = 0


class ReactionRead(BaseModel):
    id: int
    signal_id: int
    user_id: int
    emoji: str
    created_at: datetime
    updated_at: datetime
