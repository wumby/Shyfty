"""Source-agnostic ingest interface.

All data sources — polled APIs and future real-time stream consumers — implement
IngestSource. The pipeline calls fetch_events() to obtain IngestEvent objects, then
passes them through the shared normalization layer regardless of origin.

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
  FUTURE KAFKA CONSUMER PLUG-IN POINT

  To add a real-time stream consumer, create a new class that implements
  IngestSource with source_type = SourceType.STREAM:

      class KafkaNBABoxscoreSource(IngestSource):
          source_name = "kafka_nba_boxscore"
          source_type = SourceType.STREAM

          def __init__(self, bootstrap_servers: str, topic: str):
              self._consumer = KafkaConsumer(topic, bootstrap_servers=bootstrap_servers)

          def fetch_events(self, **kwargs) -> Iterator[IngestEvent]:
              # Each Kafka message is one game's merged boxscore payload.
              # The consumer commits the offset only after the event is
              # written to raw_ingest_events with status="processed".
              for message in self._consumer:
                  yield IngestEvent(
                      source=self.source_name,
                      source_type=self.source_type,
                      external_id=message.key.decode(),  # game_id
                      event_timestamp=message.timestamp,
                      ingested_at=datetime.utcnow(),
                      raw_payload=json.loads(message.value),
                  )

  Register the source in IngestPipeline and the rest of the pipeline is identical
  to the API path — normalization, idempotency, and signal generation are shared.
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
"""
from __future__ import annotations

import enum
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Iterator, Optional


class SourceType(str, enum.Enum):
    API = "api"
    STREAM = "stream"


@dataclass
class IngestEvent:
    """A single normalized event from any ingest source, before domain normalization.

    Represents the minimal envelope that every source — API batch or Kafka message —
    must produce. The raw_payload carries the provider-specific data that the
    source-specific normalizer will later parse into domain objects.
    """
    source: str          # e.g. "nba_stats", "espn_nfl", "kafka_nba_boxscore"
    source_type: SourceType
    external_id: str     # unique ID within source, used as idempotency key
    event_timestamp: Optional[datetime]  # when the underlying event occurred (e.g. game date)
    ingested_at: datetime
    raw_payload: dict[str, Any] = field(default_factory=dict)


class IngestSource(ABC):
    """Abstract base for all ingest data sources.

    Each provider (NBA Stats API, future NFL API, future Kafka consumer) implements
    this interface. The pipeline treats all sources identically after fetch_events().

    Implement two methods:
      - fetch_events: produce IngestEvent objects from the source
      - load_events:  persist the events' normalized domain data into the DB

    The pipeline handles RawIngestEvent recording and signal regeneration.
    """

    @property
    @abstractmethod
    def source_name(self) -> str:
        """Stable identifier for this source, stored in raw_ingest_events.source."""
        ...

    @property
    @abstractmethod
    def source_type(self) -> SourceType:
        """How events arrive: API poll (batch) or stream consumer (real-time)."""
        ...

    @abstractmethod
    def fetch_events(self, **kwargs) -> Iterator[IngestEvent]:
        """Yield IngestEvent objects from this source.

        API sources: fetch a batch and yield one event per game.
        Stream consumers: yield events continuously as messages arrive.
        """
        ...

    @abstractmethod
    def load_events(self, db, events: list[IngestEvent]) -> "LoadSummary":
        """Normalize and upsert a batch of IngestEvents into the DB.

        Must be idempotent: calling with the same events twice must not
        create duplicate rows (check via source_system + source_game_id + source_player_id).
        """
        ...


@dataclass(frozen=True)
class LoadSummary:
    """Counts returned by IngestSource.load_events()."""
    teams_loaded: int = 0
    players_loaded: int = 0
    games_loaded: int = 0
    stats_loaded: int = 0
    skipped_stat_rows: int = 0
    affected_player_ids: list[int] = field(default_factory=list)
