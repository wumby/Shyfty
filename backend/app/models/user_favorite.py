from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class UserFavorite(Base):
    __tablename__ = "user_favorites"
    __table_args__ = (UniqueConstraint("user_id", "signal_id", name="uq_user_signal_favorite"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id"), nullable=False, index=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
