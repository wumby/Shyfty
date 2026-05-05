from typing import Optional

from sqlalchemy import ForeignKey, String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class Player(Base):
    __tablename__ = "players"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(128), nullable=False)
    league_id: Mapped[int] = mapped_column(ForeignKey("leagues.id"), nullable=False)
    team_id: Mapped[int] = mapped_column(ForeignKey("teams.id"), nullable=False)
    position: Mapped[str] = mapped_column(String(32), nullable=False)
    source_system: Mapped[Optional[str]] = mapped_column(String(32), nullable=True)
    source_id: Mapped[Optional[str]] = mapped_column(String(64), nullable=True)

    league = relationship("League", back_populates="players")
    team = relationship("Team", back_populates="players")
    stats = relationship("PlayerGameStat", back_populates="player")
    rolling_metrics = relationship("RollingMetric", back_populates="player")
    shyfts = relationship("Shyft", back_populates="player")
