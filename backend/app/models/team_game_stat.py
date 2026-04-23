from typing import Optional

from sqlalchemy import Float, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class TeamGameStat(Base):
    __tablename__ = "team_game_stats"
    __table_args__ = (
        UniqueConstraint("source_system", "source_game_id", "source_team_id", name="uq_team_game_stat_source"),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    game_id: Mapped[int] = mapped_column(ForeignKey("games.id"), nullable=False)
    opponent_team_id: Mapped[Optional[int]] = mapped_column(ForeignKey("teams.id"), nullable=True)
    opponent_name: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    home_away: Mapped[Optional[str]] = mapped_column(String(8), nullable=True)
    points: Mapped[Optional[int]] = mapped_column(Integer)
    rebounds: Mapped[Optional[int]] = mapped_column(Integer)
    assists: Mapped[Optional[int]] = mapped_column(Integer)
    fg_pct: Mapped[Optional[float]] = mapped_column(Float)
    fg3_pct: Mapped[Optional[float]] = mapped_column(Float)
    turnovers: Mapped[Optional[int]] = mapped_column(Integer)
    pace: Mapped[Optional[float]] = mapped_column(Float)
    off_rating: Mapped[Optional[float]] = mapped_column(Float)
    source_system: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    source_game_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    source_team_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)
    raw_snapshot_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_traditional_payload_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_advanced_payload_path: Mapped[Optional[str]] = mapped_column(String(255), nullable=True)
    raw_record_index: Mapped[Optional[int]] = mapped_column(Integer, nullable=True)

    team = relationship("Team", foreign_keys=[team_id], back_populates="team_game_stats")
    opponent_team = relationship("Team", foreign_keys=[opponent_team_id])
    game = relationship("Game", back_populates="team_stats")
    source_signals = relationship(
        "Signal",
        back_populates="source_team_stat",
        foreign_keys="Signal.source_team_stat_id",
    )
