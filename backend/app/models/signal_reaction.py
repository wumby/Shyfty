from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class SignalReaction(Base):
    __tablename__ = "signal_reactions"
    __table_args__ = (UniqueConstraint("user_id", "signal_id", "type", name="uq_user_signal_reaction_emoji"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    signal_id: Mapped[int] = mapped_column(ForeignKey("signals.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="reactions")
    signal = relationship("Signal", back_populates="reactions")
