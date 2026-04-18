from datetime import datetime
from typing import Optional

from sqlalchemy import Boolean, DateTime, Float, ForeignKey, Integer, JSON, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RollingMetric(Base):
    __tablename__ = "rolling_metrics"
    __table_args__ = (UniqueConstraint("player_id", "game_id", "metric_name", name="uq_player_game_metric"),)

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), nullable=False)
    source_stat_id: Mapped[Optional[int]] = mapped_column(ForeignKey("player_game_stats.id"), nullable=True)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    rolling_avg: Mapped[float] = mapped_column(Float, nullable=False)
    rolling_stddev: Mapped[float] = mapped_column(Float, nullable=False)
    z_score: Mapped[float] = mapped_column(Float, nullable=False)
    short_window_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    medium_window_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    season_window_size: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    short_values: Mapped[Optional[list[float]]] = mapped_column(JSON, nullable=True)
    medium_values: Mapped[Optional[list[float]]] = mapped_column(JSON, nullable=True)
    season_values: Mapped[Optional[list[float]]] = mapped_column(JSON, nullable=True)
    short_rolling_avg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    short_rolling_stddev: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    short_z_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    medium_rolling_avg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    medium_rolling_stddev: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    medium_z_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    season_rolling_avg: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    season_rolling_stddev: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    season_z_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    ewma: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    recent_delta: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    trend_slope: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volatility_index: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    volatility_delta: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    opponent_average_allowed: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    opponent_rank: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)
    pace_proxy: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    usage_shift: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    high_volatility: Mapped[Optional[bool]] = mapped_column(Boolean, nullable=True)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    player = relationship("Player", back_populates="rolling_metrics")
    game = relationship("Game", back_populates="rolling_metrics")
    source_stat = relationship("PlayerGameStat", back_populates="source_rolling_metrics", foreign_keys=[source_stat_id])
    baseline_samples = relationship(
        "RollingMetricBaselineSample",
        back_populates="rolling_metric",
        order_by="RollingMetricBaselineSample.sample_order",
    )
    signals = relationship("Signal", back_populates="rolling_metric")
