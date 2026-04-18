from datetime import datetime

from pydantic import BaseModel, Field


class CommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=2000)


class CommentRead(BaseModel):
    id: int
    signal_id: int
    user_id: int
    user_email: str
    body: str
    created_at: datetime
