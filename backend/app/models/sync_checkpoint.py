from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class SyncCheckpoint(Base):
    __tablename__ = "sync_checkpoints"
    __table_args__ = (
        UniqueConstraint("source", "checkpoint_key", name="uq_sync_checkpoint_source_key"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    checkpoint_key: Mapped[str] = mapped_column(String(64), nullable=False)
    checkpoint_value: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    checkpoint_metadata: Mapped[Optional[str]] = mapped_column(Text, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)
