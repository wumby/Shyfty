from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Signal(Base):
    __tablename__ = "signals"
    __table_args__ = (
        UniqueConstraint("player_id", "game_id", "metric_name", "signal_type", name="uq_signal_generation_context"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[int] = mapped_column(ForeignKey("players.id"), nullable=False)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), nullable=False)
    rolling_metric_id: Mapped[Optional[int]] = mapped_column(ForeignKey("rolling_metrics.id"), nullable=True)
    source_stat_id: Mapped[Optional[int]] = mapped_column(ForeignKey("player_game_stats.id"), nullable=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"), nullable=False)
    signal_type: Mapped[str] = mapped_column(String(32), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    current_value: Mapped[float] = mapped_column(Float, nullable=False)
    baseline_value: Mapped[float] = mapped_column(Float, nullable=False)
    z_score: Mapped[float] = mapped_column(Float, nullable=False)
    signal_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    score_explanation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    explanation: Mapped[str] = mapped_column(String(255), nullable=False)
    narrative_summary: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    player = relationship("Player", back_populates="signals")
    game = relationship("Game", back_populates="signals")
    league = relationship("League", back_populates="signals")
    rolling_metric = relationship("RollingMetric", back_populates="signals")
    source_stat = relationship("PlayerGameStat", back_populates="source_signals", foreign_keys=[source_stat_id])
    reactions = relationship("SignalReaction", back_populates="signal", cascade="all, delete-orphan")
    comments = relationship("SignalComment", back_populates="signal", cascade="all, delete-orphan")
