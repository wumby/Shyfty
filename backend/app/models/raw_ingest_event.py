"""Raw event storage for all ingest sources.

Every event processed by the pipeline — whether from a polled API or a future Kafka
stream consumer — is recorded here before normalization. This provides:
  - Replayability: re-run normalization + signal generation from stored raw payloads
  - Idempotency: the (source, external_id) unique constraint prevents double-processing
  - Provenance: full audit trail from raw message → player_game_stat → signal

Future Kafka consumer plug-in point:
    When a Kafka consumer is added, each consumed message (e.g. one game's boxscore)
    maps to one RawIngestEvent row. The consumer checks the unique constraint before
    writing — if the row already exists with status="processed", the message is skipped.
"""
from __future__ import annotations

from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base


class RawIngestEvent(Base):
    __tablename__ = "raw_ingest_events"
    __table_args__ = (
        UniqueConstraint("source", "external_id", name="uq_raw_ingest_event"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)

    # Where the event came from
    source: Mapped[str] = mapped_column(String(64), nullable=False, index=True)
    source_type: Mapped[str] = mapped_column(String(16), nullable=False)  # "api" or "stream"

    # Unique identifier within the source system (e.g. game_id for NBA Stats API)
    external_id: Mapped[str] = mapped_column(String(128), nullable=False, index=True)

    # Timestamps
    event_timestamp: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    ingested_at: Mapped[datetime] = mapped_column(DateTime, nullable=False, default=datetime.utcnow)

    # Full raw payload as JSON text — the exact bytes received from the source
    raw_payload: Mapped[Optional[str]] = mapped_column(Text, nullable=True)

    # Processing state: "pending" | "processed" | "failed"
    status: Mapped[str] = mapped_column(String(16), nullable=False, default="processed")
