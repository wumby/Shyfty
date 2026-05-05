from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserPreference(Base):
    __tablename__ = "user_preferences"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, unique=True, index=True)
    preferred_league: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    preferred_shyft_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    default_sort_mode: Mapped[str] = mapped_column(String(32), default="newest", nullable=False)
    default_feed_mode: Mapped[str] = mapped_column(String(32), default="all", nullable=False)
    notification_releases: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    notification_digest: Mapped[bool] = mapped_column(Boolean, default=False, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
