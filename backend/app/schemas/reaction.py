from datetime import datetime
from typing import Literal

from pydantic import BaseModel


ReactionType = Literal["strong", "agree", "risky"]


class ReactionWrite(BaseModel):
    type: ReactionType


class ReactionSummaryRead(BaseModel):
    strong: int = 0
    agree: int = 0
    risky: int = 0


class ReactionRead(BaseModel):
    id: int
    signal_id: int
    user_id: int
    type: ReactionType
    created_at: datetime
    updated_at: datetime
