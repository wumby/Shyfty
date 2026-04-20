from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import json
import logging
from pathlib import Path
from typing import Any, Optional

from nba_api.live.nba.endpoints import boxscore as live_boxscore
from nba_api.stats.endpoints import (
    BoxScoreUsageV2,
    CommonAllPlayers,
    CommonTeamRoster,
    LeagueGameLog,
)


NBA_SOURCE_SYSTEM = "nba_stats"
logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class FetchResult:
    output_dir: Path
    manifest_path: Path
    game_count: int
    team_count: int
    roster_count: int
    skipped_games: int


def repo_root() -> Path:
    return Path(__file__).resolve().parents[3]


def raw_nba_root() -> Path:
    return repo_root() / "data" / "raw" / "nba"


def _to_rows(payload: dict[str, Any], dataset_name: str) -> list[dict[str, Any]]:
    result_sets = payload.get("resultSets")
    if isinstance(result_sets, list):
        matching = next((d for d in result_sets if d.get("name") == dataset_name), None)
        if matching is None:
            raise KeyError(f"Dataset {dataset_name} not found in payload.")
        headers = matching["headers"]
        return [dict(zip(headers, row)) for row in matching["rowSet"]]

    data_sets = payload.get("data_sets", {})
    if dataset_name not in data_sets:
        raise KeyError(f"Dataset {dataset_name} not found in payload.")
    headers = data_sets[dataset_name]
    rows = payload["result_set"]
    return [dict(zip(headers, row)) for row in rows]


def _has_dataset(payload: dict[str, Any], dataset_name: str) -> bool:
    result_sets = payload.get("resultSets")
    if isinstance(result_sets, list):
        return any(d.get("name") == dataset_name for d in result_sets)

    data_sets = payload.get("data_sets", {})
    return dataset_name in data_sets


def _format_live_minutes(raw_minutes: Optional[str]) -> str:
    if not raw_minutes:
        return "0:00"

    value = str(raw_minutes).strip()
    if not value.startswith("PT"):
        return value

    minutes = 0
    seconds = 0.0
    body = value[2:]
    if "M" in body:
        minute_part, body = body.split("M", 1)
        minutes = int(float(minute_part or 0))
    if body.endswith("S"):
        seconds = float(body[:-1] or 0)

    return f"{minutes}:{int(seconds):02d}"


def _build_live_traditional_payload(game_id: str) -> dict[str, Any]:
    game = live_boxscore.BoxScore(game_id=game_id).get_dict()["game"]
    game_date = str(game.get("gameEt") or game.get("gameTimeUTC") or "").split("T", 1)[0]

    home_team = game["homeTeam"]
    away_team = game["awayTeam"]
    home_tricode = home_team.get("teamTricode", "HOME")
    away_tricode = away_team.get("teamTricode", "AWAY")

    player_rows: list[list[Any]] = []
    team_rows: list[list[Any]] = []

    def append_team(team: dict[str, Any], *, is_home: bool) -> None:
        team_id = team["teamId"]
        team_name = f"{team.get('teamCity', '').strip()} {team.get('teamName', '').strip()}".strip()
        team_tricode = team.get("teamTricode", "")
        opponent_tricode = away_tricode if is_home else home_tricode
        matchup = f"{team_tricode} vs. {opponent_tricode}" if is_home else f"{team_tricode} @ {opponent_tricode}"

        for player in team.get("players", []):
            stats = player.get("statistics", {})
            player_rows.append([
                game_id,
                team_id,
                team_tricode,
                team.get("teamCity", ""),
                player["personId"],
                player["name"],
                player.get("position") or "",
                "",
                _format_live_minutes(stats.get("minutes")),
                stats.get("reboundsTotal"),
                stats.get("assists"),
                stats.get("points"),
                stats.get("steals"),
                stats.get("blocks"),
                stats.get("turnovers"),
                stats.get("plusMinusPoints"),
                stats.get("fieldGoalsPercentage"),
                stats.get("threePointersPercentage"),
                stats.get("freeThrowsPercentage"),
                matchup,
                game_date,
                team_name,
            ])

        team_stats = team.get("statistics", {})
        team_rows.append([
            game_id,
            team_id,
            team_name,
            team_tricode,
            team.get("teamCity", ""),
            _format_live_minutes(team_stats.get("minutes")),
            team_stats.get("fieldGoalsMade"),
            team_stats.get("fieldGoalsAttempted"),
            team_stats.get("fieldGoalsPercentage"),
            team_stats.get("threePointersMade"),
            team_stats.get("threePointersAttempted"),
            team_stats.get("threePointersPercentage"),
            team_stats.get("freeThrowsMade"),
            team_stats.get("freeThrowsAttempted"),
            team_stats.get("freeThrowsPercentage"),
            team_stats.get("reboundsOffensive"),
            team_stats.get("reboundsDefensive"),
            team_stats.get("reboundsTotal"),
            team_stats.get("assists"),
            team_stats.get("steals"),
            team_stats.get("blocks"),
            team_stats.get("turnovers"),
            team_stats.get("foulsPersonal"),
            team_stats.get("points"),
            team_stats.get("plusMinusPoints"),
        ])

    append_team(home_team, is_home=True)
    append_team(away_team, is_home=False)

    return {
        "resource": "boxscoretraditionalv2_live",
        "parameters": {
            "GameID": game_id,
        },
        "resultSets": [
            {
                "name": "PlayerStats",
                "headers": [
                    "GAME_ID",
                    "TEAM_ID",
                    "TEAM_ABBREVIATION",
                    "TEAM_CITY",
                    "PLAYER_ID",
                    "PLAYER_NAME",
                    "START_POSITION",
                    "COMMENT",
                    "MIN",
                    "REB",
                    "AST",
                    "PTS",
                    "STL",
                    "BLK",
                    "TO",
                    "PLUS_MINUS",
                    "FG_PCT",
                    "FG3_PCT",
                    "FT_PCT",
                    "MATCHUP",
                    "GAME_DATE",
                    "TEAM_NAME",
                ],
                "rowSet": player_rows,
            },
            {
                "name": "TeamStats",
                "headers": [
                    "GAME_ID",
                    "TEAM_ID",
                    "TEAM_NAME",
                    "TEAM_ABBREVIATION",
                    "TEAM_CITY",
                    "MIN",
                    "FGM",
                    "FGA",
                    "FG_PCT",
                    "FG3M",
                    "FG3A",
                    "FG3_PCT",
                    "FTM",
                    "FTA",
                    "FT_PCT",
                    "OREB",
                    "DREB",
                    "REB",
                    "AST",
                    "STL",
                    "BLK",
                    "TO",
                    "PF",
                    "PTS",
                    "PLUS_MINUS",
                ],
                "rowSet": team_rows,
            },
        ],
    }


def _write_json(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2), encoding="utf-8")


def _normalize_season(season: Optional[str]) -> str:
    if season:
        return season
    today = date.today()
    start_year = today.year if today.month >= 10 else today.year - 1
    return f"{start_year}-{str(start_year + 1)[-2:]}"


def _iso_date(value: date) -> str:
    return value.isoformat()


def fetch_recent_nba_data(
    *,
    season: Optional[str] = None,
    season_type: str = "Regular Season",
    days_back: int = 21,
    max_games: int = 50,
    output_root: Optional[Path] = None,
    date_from_override: Optional[date] = None,
    date_to_override: Optional[date] = None,
    sleep_between_games: float = 1.0,
) -> FetchResult:
    """Fetch NBA data via nba_api and write a raw snapshot to disk.

    sleep_between_games: seconds to sleep between per-game API calls. Defaults
        to 1.0s; also applied between traditional and usage calls per game.
    """
    import time

    season_value = _normalize_season(season)
    today = date.today()
    date_to = date_to_override or today
    date_from = date_from_override or (today - timedelta(days=days_back))
    output_root = output_root or raw_nba_root()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = output_root / f"{stamp}_{season_value.replace('-', '_')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    league_game_log_payload = LeagueGameLog(
        counter=0,
        direction="DESC",
        league_id="00",
        player_or_team_abbreviation="T",
        season=season_value,
        season_type_all_star=season_type,
        sorter="DATE",
        date_from_nullable=_iso_date(date_from),
        date_to_nullable=_iso_date(date_to),
    ).get_dict()
    _write_json(output_dir / "leaguegamelog.json", league_game_log_payload)
    game_rows = _to_rows(league_game_log_payload, "LeagueGameLog")

    deduped_games: dict[str, dict[str, Any]] = {}
    for row in game_rows:
        deduped_games.setdefault(str(row["GAME_ID"]), row)

    selected_game_ids = list(deduped_games.keys())[:max_games]
    selected_rows = [row for row in game_rows if str(row["GAME_ID"]) in selected_game_ids]
    team_ids = sorted({int(row["TEAM_ID"]) for row in selected_rows})

    all_players_payload = CommonAllPlayers(
        is_only_current_season=0,
        league_id="00",
        season=season_value,
    ).get_dict()
    _write_json(output_dir / "commonallplayers.json", all_players_payload)

    roster_dir = output_dir / "rosters"
    roster_count = 0
    for team_id in team_ids:
        payload = CommonTeamRoster(
            team_id=team_id,
            season=season_value,
        ).get_dict()
        _write_json(roster_dir / f"{team_id}.json", payload)
        roster_count += 1
        if sleep_between_games > 0:
            time.sleep(sleep_between_games)

    skipped_games = 0
    for game_id in selected_game_ids:
        if sleep_between_games > 0:
            time.sleep(sleep_between_games)
        try:
            traditional = _build_live_traditional_payload(game_id)
        except Exception:
            skipped_games += 1
            continue

        _write_json(output_dir / "games" / f"{game_id}_traditional.json", traditional)

        usage: dict[str, Any] = {}
        try:
            if sleep_between_games > 0:
                time.sleep(sleep_between_games)
            usage = BoxScoreUsageV2(game_id=game_id).get_dict()
        except Exception as exc:
            logger.warning("NBA usage boxscore fetch failed for game %s: %s", game_id, exc)

        if _has_dataset(usage, "sqlPlayersUsage"):
            _write_json(output_dir / "games" / f"{game_id}_usage.json", usage)
        else:
            logger.info("NBA usage boxscore unavailable for game %s; continuing without usage payload", game_id)

    manifest = {
        "source_system": NBA_SOURCE_SYSTEM,
        "season": season_value,
        "season_type": season_type,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "date_from": _iso_date(date_from),
        "date_to": _iso_date(date_to),
        "game_ids": selected_game_ids,
        "team_ids": team_ids,
        "skipped_games": skipped_games,
    }
    manifest_path = output_dir / "manifest.json"
    _write_json(manifest_path, manifest)
    (output_root / "LATEST").write_text(str(output_dir), encoding="utf-8")

    return FetchResult(
        output_dir=output_dir,
        manifest_path=manifest_path,
        game_count=len(selected_game_ids) - skipped_games,
        team_count=len(team_ids),
        roster_count=roster_count,
        skipped_games=skipped_games,
    )
