from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.db.base import Base


class ShyftReactionRecord(Base):
    __tablename__ = "shyft_reactions"
    __table_args__ = (UniqueConstraint("user_id", "shyft_id", "type", name="uq_user_shyft_reaction_emoji"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    shyft_id: Mapped[int] = mapped_column(ForeignKey("shyfts.id"), nullable=False, index=True)
    type: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    user = relationship("User", back_populates="reactions")
    shyft = relationship("Shyft", back_populates="reactions")

    # Backward-compatible alias for pre-rename callers.
    signal_id = synonym("shyft_id")
