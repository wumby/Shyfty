from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class PlayerGameStat(Base):
    __tablename__ = "player_game_stats"

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), nullable=False)
    points: Mapped[Optional[int]] = mapped_column(Integer)
    rebounds: Mapped[Optional[int]] = mapped_column(Integer)
    assists: Mapped[Optional[int]] = mapped_column(Integer)
    passing_yards: Mapped[Optional[int]] = mapped_column(Integer)
    rushing_yards: Mapped[Optional[int]] = mapped_column(Integer)
    receiving_yards: Mapped[Optional[int]] = mapped_column(Integer)
    touchdowns: Mapped[Optional[int]] = mapped_column(Integer)
    usage_rate: Mapped[Optional[float]] = mapped_column(Float)
    steals: Mapped[Optional[int]] = mapped_column(Integer)
    blocks: Mapped[Optional[int]] = mapped_column(Integer)
    turnovers: Mapped[Optional[int]] = mapped_column(Integer)
    minutes_played: Mapped[Optional[float]] = mapped_column(Float)
    plus_minus: Mapped[Optional[int]] = mapped_column(Integer)
    fg_pct: Mapped[Optional[float]] = mapped_column(Float)
    fg3_pct: Mapped[Optional[float]] = mapped_column(Float)
    ft_pct: Mapped[Optional[float]] = mapped_column(Float)
    source_system: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    source_game_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_player_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    raw_snapshot_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_payload_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_record_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    player = relationship("Player", back_populates="stats")
    game = relationship("Game", back_populates="stats")
    source_rolling_metrics = relationship(
        "RollingMetric",
        back_populates="source_stat",
        foreign_keys="RollingMetric.source_stat_id",
    )
    source_signals = relationship(
        "Signal",
        back_populates="source_stat",
        foreign_keys="Signal.source_stat_id",
    )
    baseline_sample_links = relationship(
        "RollingMetricBaselineSample",
        back_populates="player_game_stat",
    )
