from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class League(Base):
    __tablename__ = "leagues"

    id: Mapped[int] = mapped_column(primary_key=True)
    name: Mapped[str] = mapped_column(String(16), unique=True, nullable=False)

    teams = relationship("Team", back_populates="league")
    players = relationship("Player", back_populates="league")
    games = relationship("Game", back_populates="league")
    signals = relationship("Signal", back_populates="league")

