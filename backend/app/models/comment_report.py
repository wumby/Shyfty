from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class CommentReport(Base):
    __tablename__ = "comment_reports"
    __table_args__ = (
        UniqueConstraint("comment_id", "reporter_user_id", name="uq_comment_reporter"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    comment_id: Mapped[int] = mapped_column(ForeignKey("signal_comments.id"), nullable=False, index=True)
    reporter_user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), nullable=False, index=True)
    reason: Mapped[str] = mapped_column(String(48), nullable=False)
    notes: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    status: Mapped[str] = mapped_column(String(24), default="open", nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)
