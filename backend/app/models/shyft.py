from datetime import datetime
from typing import Optional

from sqlalchemy import DateTime, Float, ForeignKey, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship, synonym

from app.db.base import Base


class Shyft(Base):
    __tablename__ = "shyfts"
    __table_args__ = (
        UniqueConstraint("player_id", "game_id", "metric_name", "shyft_type", name="uq_shyft_generation_context"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    player_id: Mapped[Optional[int]] = mapped_column(ForeignKey("players.id"), nullable=True)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), nullable=False)
    rolling_metric_id: Mapped[Optional[int]] = mapped_column(ForeignKey("rolling_metrics.id"), nullable=True)
    source_stat_id: Mapped[Optional[int]] = mapped_column(ForeignKey("player_game_stats.id"), nullable=True)
    source_team_stat_id: Mapped[Optional[int]] = mapped_column(ForeignKey("team_game_stats.id"), nullable=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"), nullable=False)
    subject_type: Mapped[str] = mapped_column(String(16), nullable=False, default="player")
    shyft_type: Mapped[str] = mapped_column(String(32), nullable=False)
    metric_name: Mapped[str] = mapped_column(String(64), nullable=False)
    current_value: Mapped[float] = mapped_column(Float, nullable=False)
    baseline_value: Mapped[float] = mapped_column(Float, nullable=False)
    z_score: Mapped[float] = mapped_column(Float, nullable=False)
    shyft_score: Mapped[Optional[float]] = mapped_column(Float, nullable=True)
    score_explanation: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    explanation: Mapped[str] = mapped_column(String(255), nullable=False)
    narrative_summary: Mapped[Optional[str]] = mapped_column(String(512), nullable=True)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, nullable=False)

    player = relationship("Player", back_populates="shyfts")
    game = relationship("Game", back_populates="shyfts")
    league = relationship("League", back_populates="shyfts")
    rolling_metric = relationship("RollingMetric", back_populates="shyfts")
    source_stat = relationship("PlayerGameStat", back_populates="source_shyfts", foreign_keys=[source_stat_id])
    source_team_stat = relationship("TeamGameStat", back_populates="source_shyfts", foreign_keys=[source_team_stat_id])
    reactions = relationship("ShyftReactionRecord", back_populates="shyft", cascade="all, delete-orphan")
    comments = relationship("ShyftComment", back_populates="shyft", cascade="all, delete-orphan")

    # Backward-compatible aliases for pre-rename tests and operational scripts.
    signal_type = synonym("shyft_type")
    signal_score = synonym("shyft_score")
