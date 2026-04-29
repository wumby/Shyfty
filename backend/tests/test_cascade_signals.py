import unittest
from datetime import date, datetime
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.models.game import Game
from app.models.league import League
from app.models.player import Player
from app.models.signal import Signal
from app.models.team import Team
from app.schemas.signal import CascadeSignalRead, SignalRead
from app.services.signal_service import _apply_sort, _base_signal_query, _build_signal_items, detect_cascade_signals, list_signals


class CascadeSignalTests(unittest.TestCase):
    def setUp(self) -> None:
        self.temp_dir = TemporaryDirectory()
        database_path = Path(self.temp_dir.name) / "test.db"
        self.engine = create_engine(
            f"sqlite:///{database_path}",
            future=True,
            connect_args={"check_same_thread": False},
        )
        self.session_factory = sessionmaker(bind=self.engine, autoflush=False, autocommit=False, future=True)
        Base.metadata.create_all(bind=self.engine)
        self.session = self.session_factory()

        self.league = League(name="NBA")
        self.session.add(self.league)
        self.session.flush()
        self.team = Team(name="LA Clippers", league_id=self.league.id)
        self.opponent = Team(name="Denver Nuggets", league_id=self.league.id)
        self.session.add_all([self.team, self.opponent])
        self.session.flush()
        self.game = Game(
            league_id=self.league.id,
            game_date=date(2026, 1, 8),
            home_team_id=self.team.id,
            away_team_id=self.opponent.id,
        )
        self.session.add(self.game)
        self.session.flush()
        self.players = {
            name: Player(name=name, league_id=self.league.id, team_id=self.team.id, position="G")
            for name in ["Kawhi Leonard", "Norman Powell", "Bones Hyland", "P.J. Tucker", "Ivica Zubac", "James Harden"]
        }
        self.session.add_all(self.players.values())
        self.session.flush()

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
        self.temp_dir.cleanup()

    def add_signal(
        self,
        player_name: str,
        metric_name: str,
        current_value: float,
        baseline_value: float,
        signal_score: float,
        signal_type: str = "OUTLIER",
    ) -> None:
        self.session.add(
            Signal(
                player_id=self.players[player_name].id,
                game_id=self.game.id,
                team_id=self.team.id,
                league_id=self.league.id,
                subject_type="player",
                signal_type=signal_type,
                metric_name=metric_name,
                current_value=current_value,
                baseline_value=baseline_value,
                z_score=(current_value - baseline_value) / 2.0,
                signal_score=signal_score,
                score_explanation="test",
                explanation="test",
                created_at=datetime(2026, 1, 8, 12, 0, 0),
            )
        )

    def test_detects_cascade_for_minutes_dnp_and_teammate_spikes(self) -> None:
        self.add_signal("Kawhi Leonard", "minutes_played", 0, 32, 8.5)
        self.add_signal("Norman Powell", "points", 24, 16, 7.0)
        self.add_signal("Bones Hyland", "assists", 8, 4, 6.4)
        self.session.commit()

        page = list_signals(self.session, league=None, team=None, player=None, signal_type=None, limit=10)

        self.assertEqual(len(page.items), 1)
        cascade = page.items[0]
        self.assertIsInstance(cascade, CascadeSignalRead)
        assert isinstance(cascade, CascadeSignalRead)
        self.assertEqual(cascade.type, "cascade")
        self.assertEqual(cascade.trigger.player.name, "Kawhi Leonard")
        self.assertEqual([item.player.name for item in cascade.contributors], ["Norman Powell", "Bones Hyland"])
        self.assertEqual(
            cascade.narrative_summary,
            "Kawhi Leonard DNP → Norman Powell absorbed primary scoring, Bones Hyland secondary playmaking.",
        )
        self.assertEqual(len(cascade.underlying_signals), 3)

    def test_does_not_create_cascade_when_teammate_signals_are_weak(self) -> None:
        self.add_signal("Kawhi Leonard", "minutes_played", 0, 32, 8.5)
        self.add_signal("Norman Powell", "points", 21, 16, 4.9)
        self.session.commit()

        page = list_signals(self.session, league=None, team=None, player=None, signal_type=None, limit=10)

        self.assertTrue(page.items)
        self.assertTrue(all(isinstance(item, SignalRead) for item in page.items))

    def test_ranks_and_truncates_contributors(self) -> None:
        self.add_signal("Kawhi Leonard", "minutes_played", 0, 32, 8.5)
        self.add_signal("Norman Powell", "points", 24, 16, 6.0)
        self.add_signal("Bones Hyland", "assists", 9, 4, 8.0)
        self.add_signal("P.J. Tucker", "rebounds", 10, 5, 7.0)
        self.add_signal("Ivica Zubac", "points", 18, 10, 5.5)
        self.session.commit()
        rows = self.session.execute(_apply_sort(_base_signal_query(), "newest")).all()
        signals = _build_signal_items(rows, self.session, None)

        cascades = detect_cascade_signals(signals, max_contributors=3)

        self.assertEqual(len(cascades), 1)
        self.assertEqual(
            [item.player.name for item in cascades[0].contributors],
            ["Bones Hyland", "P.J. Tucker", "Norman Powell"],
        )


if __name__ == "__main__":
    unittest.main()
