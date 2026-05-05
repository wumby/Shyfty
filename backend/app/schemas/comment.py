from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class CommentCreate(BaseModel):
    body: str = Field(..., min_length=1, max_length=2000)


class CommentRead(BaseModel):
    id: int
    shyft_id: int
    user_id: int
    user_email: str
    user_display_name: str
    body: str
    created_at: datetime
    updated_at: datetime
    is_edited: bool = False
    can_edit: bool = False
    can_delete: bool = False
    can_report: bool = False


class CommentUpdate(BaseModel):
    body: str = Field(..., min_length=1, max_length=2000)


class CommentReportCreate(BaseModel):
    reason: str = Field(..., min_length=3, max_length=48)
    notes: Optional[str] = Field(default=None, max_length=1000)
