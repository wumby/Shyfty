import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.db.base import Base
from app.services.auth_service import (
    AuthError,
    authenticate_user,
    create_user,
    create_user_session,
    get_user_by_session_token,
    revoke_session,
)
from app.services.reaction_service import remove_signal_reaction, set_signal_reaction
from app.services.seed_service import seed_database
from app.services.signal_generation_service import generate_signals
from app.services.signal_service import list_signals


class AuthReactionServiceTests(unittest.TestCase):
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
        seed_database(self.session)
        generate_signals(self.session)

    def tearDown(self) -> None:
        self.session.close()
        Base.metadata.drop_all(bind=self.engine)
        self.engine.dispose()
        self.temp_dir.cleanup()

    def test_auth_and_reactions_round_trip(self) -> None:
        user = create_user(self.session, email="user@example.com", password="password123")
        self.assertEqual(user.email, "user@example.com")

        with self.assertRaises(AuthError):
            create_user(self.session, email="user@example.com", password="password123")

        authenticated = authenticate_user(self.session, email="user@example.com", password="password123")
        self.assertEqual(authenticated.id, user.id)

        session_token = create_user_session(self.session, user_id=user.id)
        current_user = get_user_by_session_token(self.session, session_token)
        self.assertIsNotNone(current_user)
        assert current_user is not None
        self.assertEqual(current_user.id, user.id)

        signal = list_signals(
            db=self.session,
            league=None,
            team=None,
            player=None,
            signal_type=None,
            limit=1,
            current_user_id=user.id,
        )[0]
        self.assertEqual(signal.reaction_summary.model_dump(mode="json"), {"strong": 0, "agree": 0, "risky": 0})
        self.assertIsNone(signal.user_reaction)

        set_signal_reaction(self.session, signal_id=signal.id, user_id=user.id, reaction_type="agree")
        agreed = list_signals(
            db=self.session,
            league=None,
            team=None,
            player=None,
            signal_type=None,
            limit=1,
            current_user_id=user.id,
        )[0]
        self.assertEqual(agreed.reaction_summary.agree, 1)
        self.assertEqual(agreed.user_reaction, "agree")

        set_signal_reaction(self.session, signal_id=signal.id, user_id=user.id, reaction_type="risky")
        risky = list_signals(
            db=self.session,
            league=None,
            team=None,
            player=None,
            signal_type=None,
            limit=1,
            current_user_id=user.id,
        )[0]
        self.assertEqual(risky.reaction_summary.agree, 0)
        self.assertEqual(risky.reaction_summary.risky, 1)
        self.assertEqual(risky.user_reaction, "risky")

        remove_signal_reaction(self.session, signal_id=signal.id, user_id=user.id)
        cleared = list_signals(
            db=self.session,
            league=None,
            team=None,
            player=None,
            signal_type=None,
            limit=1,
            current_user_id=user.id,
        )[0]
        self.assertEqual(cleared.reaction_summary.model_dump(mode="json"), {"strong": 0, "agree": 0, "risky": 0})
        self.assertIsNone(cleared.user_reaction)

        revoke_session(self.session, session_token)
        self.assertIsNone(get_user_by_session_token(self.session, session_token))
