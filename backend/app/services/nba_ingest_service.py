from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta, timezone
import json
from pathlib import Path
from typing import Any, Optional
from urllib.parse import urlencode
from urllib.request import Request, urlopen


NBA_SOURCE_SYSTEM = "nba_stats"
NBA_BASE_URL = "https://stats.nba.com/stats"
DEFAULT_HEADERS = {
    "User-Agent": "Mozilla/5.0",
    "Referer": "https://www.nba.com/",
    "Origin": "https://www.nba.com",
    "Accept": "application/json, text/plain, */*",
    "Accept-Language": "en-US,en;q=0.9",
}


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


def _request_json(endpoint: str, params: dict[str, Any]) -> dict[str, Any]:
    url = f"{NBA_BASE_URL}/{endpoint}?{urlencode(params)}"
    request = Request(url, headers=DEFAULT_HEADERS)
    with urlopen(request, timeout=30) as response:
        return json.loads(response.read().decode("utf-8"))


def _to_rows(payload: dict[str, Any], dataset_name: str) -> list[dict[str, Any]]:
    result_sets = payload.get("resultSets")
    if isinstance(result_sets, list):
        matching = next((dataset for dataset in result_sets if dataset.get("name") == dataset_name), None)
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
    max_games: int = 20,
    output_root: Optional[Path] = None,
) -> FetchResult:
    season_value = _normalize_season(season)
    today = date.today()
    date_from = today - timedelta(days=days_back)
    output_root = output_root or raw_nba_root()
    stamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_dir = output_root / f"{stamp}_{season_value.replace('-', '_')}"
    output_dir.mkdir(parents=True, exist_ok=True)

    league_game_log = _request_json(
        "leaguegamelog",
        {
            "Counter": 0,
            "Direction": "DESC",
            "LeagueID": "00",
            "PlayerOrTeam": "T",
            "Season": season_value,
            "SeasonType": season_type,
            "Sorter": "DATE",
            "DateFrom": _iso_date(date_from),
            "DateTo": _iso_date(today),
        },
    )
    _write_json(output_dir / "leaguegamelog.json", league_game_log)
    game_rows = _to_rows(league_game_log, "LeagueGameLog")

    deduped_games: dict[str, dict[str, Any]] = {}
    for row in game_rows:
        deduped_games.setdefault(str(row["GAME_ID"]), row)

    selected_game_ids = list(deduped_games.keys())[:max_games]
    selected_rows = [row for row in game_rows if str(row["GAME_ID"]) in selected_game_ids]
    team_ids = sorted({int(row["TEAM_ID"]) for row in selected_rows})

    all_players = _request_json(
        "commonallplayers",
        {"IsOnlyCurrentSeason": 1, "LeagueID": "00", "Season": season_value},
    )
    _write_json(output_dir / "commonallplayers.json", all_players)

    roster_dir = output_dir / "rosters"
    roster_count = 0
    for team_id in team_ids:
        payload = _request_json("commonteamroster", {"LeagueID": "00", "Season": season_value, "TeamID": team_id})
        _write_json(roster_dir / f"{team_id}.json", payload)
        roster_count += 1

    skipped_games = 0
    for game_id in selected_game_ids:
        try:
            traditional = _request_json(
                "boxscoretraditionalv2",
                {
                    "EndPeriod": 10,
                    "EndRange": 0,
                    "GameID": game_id,
                    "RangeType": 0,
                    "StartPeriod": 1,
                    "StartRange": 0,
                },
            )
            usage = _request_json(
                "boxscoreusagev2",
                {
                    "EndPeriod": 10,
                    "EndRange": 0,
                    "GameID": game_id,
                    "RangeType": 0,
                    "StartPeriod": 1,
                    "StartRange": 0,
                },
            )
        except Exception:
            skipped_games += 1
            continue

        _write_json(output_dir / "games" / f"{game_id}_traditional.json", traditional)
        _write_json(output_dir / "games" / f"{game_id}_usage.json", usage)

    manifest = {
        "source_system": NBA_SOURCE_SYSTEM,
        "season": season_value,
        "season_type": season_type,
        "fetched_at": datetime.now(timezone.utc).isoformat(),
        "date_from": _iso_date(date_from),
        "date_to": _iso_date(today),
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
