from __future__ import annotations

import json
import logging
from dataclasses import dataclass
from datetime import date
from typing import Any, Callable, Optional
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

logger = logging.getLogger(__name__)

NFL_SOURCE_SYSTEM = "espn_nfl"

_ESPN_NFL_BASE = "https://site.api.espn.com/apis/site/v2/sports/football/nfl"


class ESPNRequestError(RuntimeError):
    pass


def _http_get_json(url: str, timeout_seconds: float) -> Any:
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "Mozilla/5.0"})
    try:
        with urlopen(request, timeout=timeout_seconds) as response:
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="ignore")
        raise ESPNRequestError(f"ESPN request failed for {url}: {exc.code} {detail}") from exc
    except URLError as exc:
        raise ESPNRequestError(f"ESPN request failed for {url}: {exc.reason}") from exc


def _safe_int(value: Any) -> Optional[int]:
    if value is None:
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except (ValueError, TypeError):
        return None


def _extract_stat(labels: list[str], stats: list[str], *label_options: str) -> Optional[str]:
    upper_map = {lbl.upper(): i for i, lbl in enumerate(labels)}
    for lbl in label_options:
        idx = upper_map.get(lbl.upper())
        if idx is not None and idx < len(stats):
            val = str(stats[idx]).strip()
            if val and val not in ("--", "-"):
                return val
    return None


def _parse_player_stats(boxscore_players: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse ESPN boxscore.players into normalized per-player stat dicts."""
    player_stats: dict[str, dict[str, Any]] = {}

    for team_entry in boxscore_players:
        team_id = str((team_entry.get("team") or {}).get("id", ""))

        for stat_category in team_entry.get("statistics", []):
            category = stat_category.get("name", "").lower()
            labels: list[str] = stat_category.get("labels") or stat_category.get("names") or []

            for athlete_entry in stat_category.get("athletes", []):
                athlete = athlete_entry.get("athlete") or {}
                athlete_id = str(athlete.get("id", ""))
                if not athlete_id:
                    continue
                stats: list[str] = athlete_entry.get("stats") or []

                if athlete_id not in player_stats:
                    pos = (athlete.get("position") or {}).get("abbreviation") or "UNK"
                    player_stats[athlete_id] = {
                        "PlayerID": athlete_id,
                        "TeamID": team_id,
                        "Name": athlete.get("displayName") or f"Player {athlete_id}",
                        "Position": pos,
                    }

                row = player_stats[athlete_id]

                if category == "passing":
                    yds = _extract_stat(labels, stats, "YDS", "NET YDS")
                    if yds:
                        row["PassingYards"] = _safe_int(yds)
                    td = _extract_stat(labels, stats, "TD")
                    if td:
                        row["PassingTouchdowns"] = _safe_int(td)
                    catt = _extract_stat(labels, stats, "C/ATT")
                    if catt and "/" in catt:
                        row["PassingAttempts"] = _safe_int(catt.split("/")[1])

                elif category == "rushing":
                    yds = _extract_stat(labels, stats, "YDS")
                    if yds:
                        row["RushingYards"] = _safe_int(yds)
                    td = _extract_stat(labels, stats, "TD")
                    if td:
                        row["RushingTouchdowns"] = _safe_int(td)
                    car = _extract_stat(labels, stats, "CAR")
                    if car:
                        row["RushingAttempts"] = _safe_int(car)

                elif category == "receiving":
                    yds = _extract_stat(labels, stats, "YDS")
                    if yds:
                        row["ReceivingYards"] = _safe_int(yds)
                    td = _extract_stat(labels, stats, "TD")
                    if td:
                        row["ReceivingTouchdowns"] = _safe_int(td)
                    rec = _extract_stat(labels, stats, "REC")
                    if rec:
                        row["Receptions"] = _safe_int(rec)
                    tgt = _extract_stat(labels, stats, "TGTS", "TGT")
                    if tgt:
                        row["Targets"] = _safe_int(tgt)

    return list(player_stats.values())


def _default_season_candidates(today: Optional[date] = None) -> list[int]:
    d = today or date.today()
    # NFL season year = the calendar year the season kicks off (September).
    # Jan–July: the most recent completed season started the prior year.
    if d.month <= 7:
        return [d.year - 1, d.year - 2]
    return [d.year, d.year - 1]


@dataclass(frozen=True)
class NFLFetchWindow:
    season: int
    week: int
    season_type: int
    games_found: int


@dataclass(frozen=True)
class NFLFetchResult:
    teams: list[dict[str, Any]]
    players: list[dict[str, Any]]
    boxscores: list[dict[str, Any]]
    windows: list[NFLFetchWindow]

    @property
    def game_count(self) -> int:
        return len(self.boxscores)


class ESPNNFLClient:
    def __init__(
        self,
        *,
        base_url: Optional[str] = None,
        timeout_seconds: float = 20.0,
        fetch_json: Optional[Callable[[str, float], Any]] = None,
    ) -> None:
        self._base_url = (base_url or _ESPN_NFL_BASE).rstrip("/")
        self._timeout_seconds = timeout_seconds
        self._fetch_json = fetch_json or _http_get_json

    def _get(self, path: str, **params: Any) -> Any:
        query = "&".join(f"{k}={v}" for k, v in params.items() if v is not None)
        url = f"{self._base_url}/{path.lstrip('/')}"
        if query:
            url = f"{url}?{query}"
        return self._fetch_json(url, self._timeout_seconds)

    def fetch_teams(self) -> list[dict[str, Any]]:
        data = self._get("teams", limit=32)
        teams = []
        for sport in data.get("sports") or []:
            for league in sport.get("leagues") or []:
                for entry in league.get("teams") or []:
                    t = entry.get("team") or {}
                    team_id = str(t.get("id", ""))
                    if not team_id:
                        continue
                    teams.append({
                        "TeamID": team_id,
                        "Key": t.get("abbreviation", ""),
                        "FullName": t.get("displayName") or t.get("name") or team_id,
                    })
        return teams

    def fetch_scoreboard(self, *, season: int, week: int, season_type: int = 2) -> list[dict[str, Any]]:
        """Returns completed-game event metadata for a given season/week."""
        data = self._get("scoreboard", season=season, seasontype=season_type, week=week)
        completed = []
        for event in data.get("events") or []:
            competitions = event.get("competitions") or []
            if not competitions:
                continue
            comp = competitions[0]
            if not (comp.get("status") or {}).get("type", {}).get("completed"):
                continue
            competitors = comp.get("competitors") or []
            home = next((c for c in competitors if c.get("homeAway") == "home"), None)
            away = next((c for c in competitors if c.get("homeAway") == "away"), None)
            if not home or not away:
                continue
            completed.append({
                "event_id": str(event.get("id", "")),
                "date": event.get("date") or comp.get("date"),
                "home_team_id": str((home.get("team") or {}).get("id", "")),
                "home_team_abbr": (home.get("team") or {}).get("abbreviation", ""),
                "home_score": _safe_int(home.get("score")),
                "away_team_id": str((away.get("team") or {}).get("id", "")),
                "away_team_abbr": (away.get("team") or {}).get("abbreviation", ""),
                "away_score": _safe_int(away.get("score")),
            })
        return completed

    def fetch_game_boxscore(
        self, *, event_id: str, season: int, event_meta: dict[str, Any]
    ) -> Optional[dict[str, Any]]:
        try:
            data = self._get("summary", event=event_id)
        except ESPNRequestError as exc:
            logger.warning("Skipping game %s: %s", event_id, exc)
            return None

        boxscore_section = data.get("boxscore") or {}
        header = data.get("header") or {}
        season_raw = header.get("season") or {}
        week_raw = header.get("week") or {}
        # ESPN sometimes returns these as plain ints, sometimes as {"year": ..., "number": ...}
        season_year = season_raw.get("year") if isinstance(season_raw, dict) else season_raw
        week_number = week_raw.get("number") if isinstance(week_raw, dict) else week_raw
        player_rows = _parse_player_stats(boxscore_section.get("players") or [])

        return {
            "GameID": event_id,
            "HomeTeamID": event_meta["home_team_id"],
            "HomeTeam": event_meta["home_team_abbr"],
            "HomeScore": event_meta.get("home_score"),
            "AwayTeamID": event_meta["away_team_id"],
            "AwayTeam": event_meta["away_team_abbr"],
            "AwayScore": event_meta.get("away_score"),
            "Date": event_meta["date"],
            "Season": str(season_year or season),
            "Week": week_number,
            "PlayerGames": player_rows,
        }

    def fetch_recent_completed_data(
        self,
        *,
        season: Optional[int] = None,
        weeks_back: int = 6,
        max_games: int = 80,
        today: Optional[date] = None,
    ) -> NFLFetchResult:
        teams = self.fetch_teams()
        season_candidates = [season] if season is not None else _default_season_candidates(today)

        windows: list[NFLFetchWindow] = []
        boxscores: list[dict[str, Any]] = []
        seen_event_ids: set[str] = set()

        # Scan postseason (type=3, weeks 4→1) then regular season (type=2, weeks 18→1)
        week_schedule: list[tuple[int, range]] = [
            (3, range(4, 0, -1)),
            (2, range(18, 0, -1)),
        ]

        for season_year in season_candidates:
            for season_type, week_range in week_schedule:
                for week in week_range:
                    try:
                        events = self.fetch_scoreboard(season=season_year, week=week, season_type=season_type)
                    except ESPNRequestError:
                        continue

                    new_events = [e for e in events if e["event_id"] not in seen_event_ids]
                    if not new_events:
                        continue

                    games_this_window = 0
                    for event_meta in new_events:
                        if len(boxscores) >= max_games:
                            break
                        event_id = event_meta["event_id"]
                        seen_event_ids.add(event_id)
                        boxscore = self.fetch_game_boxscore(
                            event_id=event_id, season=season_year, event_meta=event_meta
                        )
                        if boxscore:
                            boxscores.append(boxscore)
                            games_this_window += 1

                    if games_this_window > 0:
                        windows.append(
                            NFLFetchWindow(
                                season=season_year,
                                week=week,
                                season_type=season_type,
                                games_found=games_this_window,
                            )
                        )

                    if len(windows) >= weeks_back or len(boxscores) >= max_games:
                        return NFLFetchResult(teams=teams, players=[], boxscores=boxscores, windows=windows)

        return NFLFetchResult(teams=teams, players=[], boxscores=boxscores, windows=windows)
