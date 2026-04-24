import json
import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.services.signal_backtest_service import run_signal_backtest, write_backtest_result
from app.services.signal_generation_service import generate_signals
from tests.support_fixtures import load_sample_signal_dataset


class SignalBacktestServiceTests(unittest.TestCase):
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
        load_sample_signal_dataset(self.session)
        generate_signals(self.session)

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_backtest_produces_summary_and_output_file(self) -> None:
        result = run_signal_backtest(self.session)
        self.assertIn("signal_count", result.summary)
        self.assertIn("precision_next_game", result.summary)
        self.assertIn("recommended", result.thresholds)
        self.assertTrue(isinstance(result.calibration, list))

        output_path = Path(self.temp_dir.name) / "backtest.json"
        write_backtest_result(result, output_path)
        payload = json.loads(output_path.read_text(encoding="utf-8"))
        self.assertIn("summary", payload)
        self.assertIn("signal_type_metrics", payload)
        self.assertIn("calibration", payload)


if __name__ == "__main__":
    unittest.main()
