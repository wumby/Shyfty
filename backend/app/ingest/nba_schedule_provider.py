from __future__ import annotations

from datetime import date, datetime
import json
from typing import Optional

from nba_api.stats.endpoints import BoxScoreAdvancedV2, BoxScoreTraditionalV2, BoxScoreUsageV2, ScoreboardV2

from app.ingest.providers import ProviderGame, ProviderGameDetail
from app.services.nba_ingest_service import NBA_SOURCE_SYSTEM


def _parse_game_date(raw: str) -> date:
    if "T" in raw:
        return datetime.strptime(raw, "%Y-%m-%dT%H:%M:%S").date()
    return datetime.strptime(raw, "%Y-%m-%d").date()


def _normalize_status(status_text: Optional[str]) -> str:
    text = (status_text or "").strip().lower()
    if "final" in text:
        return "final"
    if "postponed" in text:
        return "postponed"
    if "cancel" in text:
        return "canceled"
    if "half" in text or "qtr" in text or "live" in text or "progress" in text:
        return "live"
    if "scheduled" in text or "pm" in text or "am" in text:
        return "scheduled"
    return "unknown"


class NBAScheduleProvider:
    league = "nba"

    def discover_schedule(self, *, start_date: date, end_date: date) -> list[ProviderGame]:
        games: dict[str, ProviderGame] = {}
        current = start_date
        while current <= end_date:
            payload = ScoreboardV2(game_date=current.strftime("%m/%d/%Y")).get_dict()
            headers = []
            rows = []
            for result in payload.get("resultSets", []):
                if result.get("name") == "GameHeader":
                    headers = result.get("headers", [])
                    rows = result.get("rowSet", [])
                    break
            for row in rows:
                record = dict(zip(headers, row))
                game_id = str(record.get("GAME_ID", "")).strip()
                if not game_id:
                    continue
                game_date_raw = str(record.get("GAME_DATE_EST") or record.get("GAME_DATE") or current.isoformat())
                game_date = _parse_game_date(game_date_raw)
                game_status_text = str(record.get("GAME_STATUS_TEXT", ""))
                provider_game = ProviderGame(
                    league=self.league,
                    external_game_id=game_id,
                    game_date=game_date,
                    status=_normalize_status(game_status_text),
                    home_team_external_id=str(record.get("HOME_TEAM_ID", "")),
                    away_team_external_id=str(record.get("VISITOR_TEAM_ID", "")),
                    raw_payload={"game_header": record},
                )
                games[game_id] = provider_game
            current = date.fromordinal(current.toordinal() + 1)
        return list(games.values())

    def fetch_game_detail(self, external_game_id: str) -> ProviderGameDetail:
        traditional = BoxScoreTraditionalV2(game_id=external_game_id).get_dict()
        advanced: dict = {}
        usage: dict = {}
        try:
            advanced = BoxScoreAdvancedV2(game_id=external_game_id).get_dict()
        except Exception:
            advanced = {}
        try:
            usage = BoxScoreUsageV2(game_id=external_game_id).get_dict()
        except Exception:
            usage = {}

        # Derive metadata from TeamStats rows.
        team_headers = []
        team_rows = []
        for result in traditional.get("resultSets", []):
            if result.get("name") == "TeamStats":
                team_headers = result.get("headers", [])
                team_rows = result.get("rowSet", [])
                break
        teams = [dict(zip(team_headers, row)) for row in team_rows]
        if len(teams) < 2:
            raise ValueError(f"NBA detail payload missing TeamStats for game {external_game_id}")

        home_row = next((r for r in teams if "vs." in str(r.get("MATCHUP", ""))), teams[0])
        away_row = next((r for r in teams if "@" in str(r.get("MATCHUP", ""))), teams[1])
        game_date_value = home_row.get("GAME_DATE") or away_row.get("GAME_DATE")
        if not game_date_value:
            raise ValueError(f"GAME_DATE missing from boxscore for game {external_game_id}")
        game_date = _parse_game_date(str(game_date_value))
        game = ProviderGame(
            league=self.league,
            external_game_id=str(external_game_id),
            game_date=game_date,
            status="final",
            home_team_external_id=str(home_row.get("TEAM_ID")),
            away_team_external_id=str(away_row.get("TEAM_ID")),
            raw_payload={"team_rows": teams},
        )

        payload = {
            "source_system": NBA_SOURCE_SYSTEM,
            "game_id": str(external_game_id),
            "snapshot_dir": "",
            "traditional": traditional,
            "advanced": advanced,
            "usage": usage,
            "game_log_meta": {
                "game_date": game_date.isoformat(),
                "home_team_id": game.home_team_external_id,
                "away_team_id": game.away_team_external_id,
            },
            "raw_detail": json.dumps({"traditional": traditional, "advanced": advanced, "usage": usage}),
        }
        return ProviderGameDetail(game=game, payload=payload)
