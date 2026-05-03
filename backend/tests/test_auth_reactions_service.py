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
from app.services.profile_service import get_profile, remove_follow, set_follow
from app.services.reaction_service import (
    MAX_REACTIONS_PER_USER_PER_SIGNAL,
    ReactionLimitError,
    remove_signal_reaction,
    set_signal_reaction,
)
from app.services.signal_generation_service import generate_signals
from app.services.signal_service import FEED_MODE_FOLLOWING, list_signals
from tests.support_fixtures import load_sample_signal_dataset


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
        load_sample_signal_dataset(self.session)
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

        first_page = list_signals(
            db=self.session,
            league=None,
            team=None,
            player=None,
            signal_type=None,
            limit=1,
            current_user_id=user.id,
        )
        self.assertEqual(len(first_page.items), 1)
        self.assertTrue(first_page.has_more)
        self.assertEqual(first_page.next_cursor, first_page.items[0].id)

        signal = first_page.items[0]
        self.assertEqual(signal.reaction_summary.model_dump(mode="json"), {"strong": 0, "agree": 0, "risky": 0})
        self.assertIsNone(signal.user_reaction)

        set_signal_reaction(self.session, signal_id=signal.id, user_id=user.id, reaction_type="agree")
        agreed_page = list_signals(
            db=self.session,
            league=None,
            team=None,
            player=None,
            signal_type=None,
            limit=1,
            current_user_id=user.id,
        )
        self.assertEqual(len(agreed_page.items), 1)
        agreed = agreed_page.items[0]
        self.assertEqual(agreed.reaction_summary.agree, 1)
        self.assertEqual(agreed.user_reaction, "agree")

        set_signal_reaction(self.session, signal_id=signal.id, user_id=user.id, reaction_type="risky")
        risky_page = list_signals(
            db=self.session,
            league=None,
            team=None,
            player=None,
            signal_type=None,
            limit=1,
            current_user_id=user.id,
        )
        self.assertEqual(len(risky_page.items), 1)
        risky = risky_page.items[0]
        self.assertEqual(risky.reaction_summary.agree, 0)
        self.assertEqual(risky.reaction_summary.risky, 1)
        self.assertEqual(risky.user_reaction, "risky")

        remove_signal_reaction(self.session, signal_id=signal.id, user_id=user.id)
        cleared_page = list_signals(
            db=self.session,
            league=None,
            team=None,
            player=None,
            signal_type=None,
            limit=1,
            current_user_id=user.id,
        )
        self.assertEqual(len(cleared_page.items), 1)
        cleared = cleared_page.items[0]
        self.assertEqual(cleared.reaction_summary.model_dump(mode="json"), {"strong": 0, "agree": 0, "risky": 0})
        self.assertIsNone(cleared.user_reaction)

        revoke_session(self.session, session_token)
        self.assertIsNone(get_user_by_session_token(self.session, session_token))

    def test_reaction_limit_is_enforced_per_user_signal(self) -> None:
        user = create_user(self.session, email="limit@example.com", password="password123")
        signal = list_signals(
            db=self.session,
            league=None,
            team=None,
            player=None,
            signal_type=None,
            limit=1,
            current_user_id=user.id,
        ).items[0]

        for index in range(MAX_REACTIONS_PER_USER_PER_SIGNAL):
            set_signal_reaction(self.session, signal_id=signal.id, user_id=user.id, emoji=f"e{index}")

        with self.assertRaises(ReactionLimitError):
            set_signal_reaction(self.session, signal_id=signal.id, user_id=user.id, emoji="one-too-many")

        remove_signal_reaction(self.session, signal_id=signal.id, user_id=user.id, emoji="e0")
        set_signal_reaction(self.session, signal_id=signal.id, user_id=user.id, emoji="replacement")

    def test_follow_round_trip_updates_profile_and_following_feed(self) -> None:
        user = create_user(self.session, email="follower@example.com", password="password123")
        signal = next(
            item
            for item in list_signals(
                db=self.session,
                league=None,
                team=None,
                player=None,
                signal_type=None,
                limit=10,
                current_user_id=user.id,
            ).items
            if item.player_id is not None
        )
        assert signal.player_id is not None

        empty_profile = get_profile(self.session, user.id)
        self.assertEqual(empty_profile.follows.players, [])
        self.assertEqual(empty_profile.follows.teams, [])
        empty_following = list_signals(
            db=self.session,
            league=None,
            team=None,
            player=None,
            signal_type=None,
            limit=10,
            current_user_id=user.id,
            feed_mode=FEED_MODE_FOLLOWING,
        )
        self.assertEqual(empty_following.items, [])

        set_follow(self.session, user.id, "player", signal.player_id)
        set_follow(self.session, user.id, "player", signal.player_id)
        followed_profile = get_profile(self.session, user.id)
        self.assertEqual(followed_profile.follows.players, [signal.player_id])
        self.assertEqual(followed_profile.follows.teams, [])

        following = list_signals(
            db=self.session,
            league=None,
            team=None,
            player=None,
            signal_type=None,
            limit=10,
            current_user_id=user.id,
            feed_mode=FEED_MODE_FOLLOWING,
        )
        self.assertTrue(following.items)
        self.assertTrue(all(item.player_id == signal.player_id for item in following.items))

        remove_follow(self.session, user.id, "player", signal.player_id)
        cleared_profile = get_profile(self.session, user.id)
        self.assertEqual(cleared_profile.follows.players, [])
        cleared_following = list_signals(
            db=self.session,
            league=None,
            team=None,
            player=None,
            signal_type=None,
            limit=10,
            current_user_id=user.id,
            feed_mode=FEED_MODE_FOLLOWING,
        )
        self.assertEqual(cleared_following.items, [])
