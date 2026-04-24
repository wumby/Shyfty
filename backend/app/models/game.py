from datetime import date, datetime
from typing import Optional

from sqlalchemy import DateTime, ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Game(Base):
    __tablename__ = "games"

    id: Mapped[int] = mapped_column(primary_key=True)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"), nullable=False)
    game_date: Mapped[date] = mapped_column(nullable=False)
    season: Mapped[Optional[str]] = mapped_column(String(7), nullable=True, index=True)
    home_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    away_team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    source_system: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    source_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    last_synced_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)
    signals_generated_at: Mapped[Optional[datetime]] = mapped_column(DateTime, nullable=True)

    league = relationship("League", back_populates="games")
    stats = relationship("PlayerGameStat", back_populates="game")
    team_stats = relationship("TeamGameStat", back_populates="game")
    rolling_metrics = relationship("RollingMetric", back_populates="game")
    signals = relationship("Signal", back_populates="game")
