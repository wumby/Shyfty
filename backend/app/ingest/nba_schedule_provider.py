from __future__ import annotations

from datetime import date, datetime
import json
import logging
from typing import Optional

from nba_api.stats.endpoints import BoxScoreAdvancedV2, BoxScoreTraditionalV2, BoxScoreUsageV2, ScoreboardV2
import requests

from app.ingest.providers import ProviderGame, ProviderGameDetail
from app.services.nba_ingest_service import NBA_SOURCE_SYSTEM

logger = logging.getLogger(__name__)

LIVE_DATA_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.nba.com/",
}


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


def _normalize_live_status(status_code: Optional[int], status_text: Optional[str]) -> str:
    if status_code == 3:
        return "final"
    if status_code == 2:
        return "live"
    return _normalize_status(status_text)


def _live_json(path: str) -> dict:
    url = f"https://cdn.nba.com/static/json/liveData/{path}"
    response = requests.get(url, headers=LIVE_DATA_HEADERS, timeout=20)
    response.raise_for_status()
    return response.json()


def _minutes_from_live_duration(raw: Optional[str]) -> str:
    if not raw:
        return "0:00"
    if not raw.startswith("PT"):
        return raw
    body = raw[2:]
    minutes = 0
    seconds = 0
    if "M" in body:
        minute_part, body = body.split("M", 1)
        try:
            minutes = int(float(minute_part))
        except ValueError:
            minutes = 0
    if "S" in body:
        second_part = body.split("S", 1)[0]
        try:
            seconds = int(float(second_part))
        except ValueError:
            seconds = 0
    return f"{minutes}:{str(seconds).zfill(2)}"


def _pct(numerator, denominator) -> float:
    try:
        denominator_value = float(denominator or 0)
        if denominator_value == 0:
            return 0.0
        return float(numerator or 0) / denominator_value
    except (TypeError, ValueError):
        return 0.0


def _team_full_name(team: dict) -> str:
    city = str(team.get("teamCity") or "").strip()
    name = str(team.get("teamName") or "").strip()
    if city and name and city not in name:
        return f"{city} {name}"
    return name or city or f"Team {team.get('teamId')}"


def _provider_game_from_live(game: dict) -> ProviderGame:
    raw_game_time = game.get("gameTimeHome") or game.get("gameEt") or game.get("gameTimeUTC")
    game_date = datetime.fromisoformat(str(raw_game_time).replace("Z", "+00:00")).date()
    return ProviderGame(
        league="nba",
        external_game_id=str(game["gameId"]),
        game_date=game_date,
        status=_normalize_live_status(game.get("gameStatus"), game.get("gameStatusText")),
        home_team_external_id=str(game["homeTeam"]["teamId"]),
        away_team_external_id=str(game["awayTeam"]["teamId"]),
        raw_payload={"live_game": game},
    )


def _live_scoreboard_for_date(target_date: date) -> list[ProviderGame]:
    payload = _live_json("scoreboard/todaysScoreboard_00.json")
    scoreboard = payload.get("scoreboard") or {}
    raw_game_date = scoreboard.get("gameDate")
    if raw_game_date != target_date.isoformat():
        return []
    return [_provider_game_from_live(game) for game in scoreboard.get("games", [])]


def _live_boxscore_to_payload(external_game_id: str) -> ProviderGameDetail:
    payload = _live_json(f"boxscore/boxscore_{external_game_id}.json")
    game_payload = payload.get("game") or {}
    game = _provider_game_from_live(game_payload)
    game_date = game.game_date.isoformat()

    player_headers = [
        "PLAYER_ID",
        "PLAYER_NAME",
        "TEAM_ID",
        "TEAM_NAME",
        "TEAM_ABBREVIATION",
        "START_POSITION",
        "MIN",
        "PTS",
        "REB",
        "AST",
        "STL",
        "BLK",
        "TO",
        "PLUS_MINUS",
        "FG_PCT",
        "FG3_PCT",
        "FT_PCT",
    ]
    team_headers = [
        "TEAM_ID",
        "TEAM_CITY",
        "TEAM_NAME",
        "TEAM_ABBREVIATION",
        "PTS",
        "REB",
        "AST",
        "FG_PCT",
        "FG3_PCT",
        "TO",
    ]

    player_rows = []
    team_rows = []
    for team_key in ("homeTeam", "awayTeam"):
        team = game_payload.get(team_key) or {}
        team_stats = team.get("statistics") or {}
        team_rows.append(
            [
                team.get("teamId"),
                team.get("teamCity"),
                team.get("teamName"),
                team.get("teamTricode"),
                team_stats.get("points"),
                team_stats.get("reboundsTotal"),
                team_stats.get("assists"),
                team_stats.get("fieldGoalsPercentage") or _pct(team_stats.get("fieldGoalsMade"), team_stats.get("fieldGoalsAttempted")),
                team_stats.get("threePointersPercentage") or _pct(team_stats.get("threePointersMade"), team_stats.get("threePointersAttempted")),
                team_stats.get("turnoversTotal") if team_stats.get("turnoversTotal") is not None else team_stats.get("turnovers"),
            ]
        )
        for player in team.get("players") or []:
            if str(player.get("played", "0")) != "1":
                continue
            stats = player.get("statistics") or {}
            player_rows.append(
                [
                    player.get("personId"),
                    player.get("name"),
                    team.get("teamId"),
                    _team_full_name(team),
                    team.get("teamTricode"),
                    player.get("position") or "",
                    _minutes_from_live_duration(stats.get("minutes")),
                    stats.get("points"),
                    stats.get("reboundsTotal"),
                    stats.get("assists"),
                    stats.get("steals"),
                    stats.get("blocks"),
                    stats.get("turnovers"),
                    stats.get("plusMinusPoints"),
                    stats.get("fieldGoalsPercentage") or _pct(stats.get("fieldGoalsMade"), stats.get("fieldGoalsAttempted")),
                    stats.get("threePointersPercentage") or _pct(stats.get("threePointersMade"), stats.get("threePointersAttempted")),
                    stats.get("freeThrowsPercentage") or _pct(stats.get("freeThrowsMade"), stats.get("freeThrowsAttempted")),
                ]
            )

    traditional = {
        "resultSets": [
            {"name": "PlayerStats", "headers": player_headers, "rowSet": player_rows},
            {"name": "TeamStats", "headers": team_headers, "rowSet": team_rows},
        ]
    }
    return ProviderGameDetail(
        game=game,
        payload={
            "source_system": NBA_SOURCE_SYSTEM,
            "game_id": str(external_game_id),
            "snapshot_dir": "",
            "traditional": traditional,
            "advanced": {},
            "usage": {},
            "game_log_meta": {
                "game_date": game_date,
                "home_team_id": game.home_team_external_id,
                "away_team_id": game.away_team_external_id,
                "status": game.status,
            },
            "raw_detail": json.dumps(payload),
        },
    )


class NBAScheduleProvider:
    league = "nba"

    def discover_schedule(self, *, start_date: date, end_date: date) -> list[ProviderGame]:
        games: dict[str, ProviderGame] = {}
        current = start_date
        while current <= end_date:
            try:
                for live_game in _live_scoreboard_for_date(current):
                    games[live_game.external_game_id] = live_game
                if any(game.game_date == current for game in games.values()):
                    current = date.fromordinal(current.toordinal() + 1)
                    continue
            except Exception as exc:
                logger.warning("NBA live schedule fallback failed for %s: %s", current.isoformat(), exc)

            try:
                payload = ScoreboardV2(game_date=current.strftime("%m/%d/%Y")).get_dict()
            except Exception as exc:
                logger.warning("Skipping NBA schedule discovery for %s: %s", current.isoformat(), exc)
                current = date.fromordinal(current.toordinal() + 1)
                continue
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
        try:
            return _live_boxscore_to_payload(external_game_id)
        except Exception as exc:
            logger.warning("NBA live boxscore fallback failed for game %s: %s", external_game_id, exc)

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
                "status": game.status,
            },
            "raw_detail": json.dumps({"traditional": traditional, "advanced": advanced, "usage": usage}),
        }
        return ProviderGameDetail(game=game, payload=payload)
