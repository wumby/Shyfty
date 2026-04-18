from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserSavedView(Base):
    __tablename__ = "user_saved_views"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    name: Mapped[str] = mapped_column(String(80), nullable=False)
    league: Mapped[Optional[str]] = mapped_column(String(16), nullable=True)
    signal_type: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    player: Mapped[Optional[str]] = mapped_column(String(120), nullable=True)
    sort_mode: Mapped[str] = mapped_column(String(32), default="newest", nullable=False)
    feed_mode: Mapped[str] = mapped_column(String(32), default="all", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)
