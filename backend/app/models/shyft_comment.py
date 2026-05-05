from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, String, Text
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class ShyftComment(Base):
    __tablename__ = "shyft_comments"

    id: Mapped[int] = mapped_column(primary_key=True)
    shyft_id: Mapped[int] = mapped_column(ForeignKey("shyfts.id"), nullable=False)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow, nullable=False)

    shyft = relationship("Shyft", back_populates="comments")
    user = relationship("User", back_populates="comments")
