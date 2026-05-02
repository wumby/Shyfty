import unittest

from app.services.nba_ingest_service import _select_game_ids_for_team_coverage


class NBAIngestSelectionTests(unittest.TestCase):
    def test_selects_additional_games_to_cover_min_games_per_team(self) -> None:
        rows = []
        # Ordered from newest to oldest:
        # First two games involve only teams 1 and 2.
        rows.extend([
            {"GAME_ID": "g1", "TEAM_ID": 1},
            {"GAME_ID": "g1", "TEAM_ID": 2},
            {"GAME_ID": "g2", "TEAM_ID": 1},
            {"GAME_ID": "g2", "TEAM_ID": 2},
            {"GAME_ID": "g3", "TEAM_ID": 3},
            {"GAME_ID": "g3", "TEAM_ID": 4},
            {"GAME_ID": "g4", "TEAM_ID": 3},
            {"GAME_ID": "g4", "TEAM_ID": 4},
        ])

        selected = _select_game_ids_for_team_coverage(rows, max_games=2, min_games_per_team=2)
        self.assertEqual(selected, ["g1", "g2", "g3", "g4"])


if __name__ == "__main__":
    unittest.main()
