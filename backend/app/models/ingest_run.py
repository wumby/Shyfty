from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, String
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class IngestRun(Base):
    __tablename__ = "ingest_runs"

    id: Mapped[int] = mapped_column(primary_key=True)
    started_at: Mapped[datetime] = mapped_column(DateTime, nullable=False)
    finished_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="running")
    error_message: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    games_fetched: Mapped[Optional[int]] = mapped_column(nullable=True)
    players_loaded: Mapped[Optional[int]] = mapped_column(nullable=True)
    shyfts_created: Mapped[Optional[int]] = mapped_column(nullable=True)
    shyfts_updated: Mapped[Optional[int]] = mapped_column(nullable=True)
    duration_seconds: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
