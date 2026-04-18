from sqlalchemy import ForeignKey, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class RollingMetricBaselineSample(Base):
    __tablename__ = "rolling_metric_baseline_samples"
    __table_args__ = (
        UniqueConstraint(
            "rolling_metric_id",
            "player_game_stat_id",
            name="uq_rolling_metric_baseline_sample",
        ),
    )

    id: Mapped[int] = mapped_column(primary_key=True)
    rolling_metric_id: Mapped[int] = mapped_column(ForeignKey("rolling_metrics.id"), nullable=False)
    player_game_stat_id: Mapped[int] = mapped_column(ForeignKey("player_game_stats.id"), nullable=False)
    sample_order: Mapped[int] = mapped_column(nullable=False)

    rolling_metric = relationship("RollingMetric", back_populates="baseline_samples")
    player_game_stat = relationship("PlayerGameStat", back_populates="baseline_sample_links")
