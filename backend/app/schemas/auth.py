from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field


class UserCreate(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)
    display_name: Optional[str] = Field(default=None, min_length=1, max_length=80)


class UserSignIn(BaseModel):
    email: str = Field(min_length=5, max_length=255)
    password: str = Field(min_length=8, max_length=128)


class PasswordChange(BaseModel):
    current_password: str = Field(min_length=8, max_length=128)
    new_password: str = Field(min_length=8, max_length=128)
    confirm_new_password: str = Field(min_length=8, max_length=128)


class UserRead(BaseModel):
    id: int
    email: str
    display_name: Optional[str] = None
    created_at: datetime


class AuthSessionRead(BaseModel):
    user: Optional[UserRead]


class AuthMessageRead(BaseModel):
    message: str
