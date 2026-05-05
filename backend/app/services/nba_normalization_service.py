from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.league import League
from app.models.player import Player
from app.models.player_game_stat import PlayerGameStat
from app.models.rolling_metric import RollingMetric
from app.models.rolling_metric_baseline_sample import RollingMetricBaselineSample
from app.models.shyft import Shyft
from app.models.team import Team
from app.models.team_game_stat import TeamGameStat
from app.domain.seasons import season_from_date
from app.services.nba_ingest_service import NBA_SOURCE_SYSTEM, raw_nba_root


@dataclass
class LoadResult:
    snapshot_dir: Optional[Path]
    teams_loaded: int
    players_loaded: int
    games_loaded: int
    stats_loaded: int
    skipped_stat_rows: int
    team_stats_loaded: int = 0
    affected_player_ids: list = field(default_factory=list)
    affected_team_ids: list = field(default_factory=list)
    affected_game_ids: list = field(default_factory=list)


def _read_json(path: Path) -> dict[str, Any]:
    return json.loads(path.read_text(encoding="utf-8"))


def _resolve_snapshot_dir(snapshot_dir: Optional[Path]) -> Path:
    if snapshot_dir:
        return snapshot_dir

    latest_path = raw_nba_root() / "LATEST"
    if latest_path.exists():
        return Path(latest_path.read_text(encoding="utf-8").strip())
    raise FileNotFoundError("No NBA raw snapshot found. Run the fetch step first.")


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


def _optional_rows(payload: Optional[dict[str, Any]], dataset_name: str) -> list[dict[str, Any]]:
    if not payload:
        return []
    try:
        return _to_rows(payload, dataset_name)
    except KeyError:
        return []


def _upsert_team(db: Session, *, league_id: int, team_name: str, source_id: str) -> Team:
    team = db.execute(
        select(Team).where(Team.source_system == NBA_SOURCE_SYSTEM, Team.source_id == source_id)
    ).scalar_one_or_none()
    if team is None:
        team = Team(name=team_name, league_id=league_id, source_system=NBA_SOURCE_SYSTEM, source_id=source_id)
        db.add(team)
        db.flush()
        return team

    team.name = team_name
    team.league_id = league_id
    return team


def _upsert_player(
    db: Session,
    *,
    league_id: int,
    team_id: int,
    player_name: str,
    position: str,
    source_id: str,
) -> Player:
    player = db.execute(
        select(Player).where(Player.source_system == NBA_SOURCE_SYSTEM, Player.source_id == source_id)
    ).scalar_one_or_none()
    if player is None:
        player = Player(
            name=player_name,
            league_id=league_id,
            team_id=team_id,
            position=position or "UNK",
            source_system=NBA_SOURCE_SYSTEM,
            source_id=source_id,
        )
        db.add(player)
        db.flush()
        return player

    player.name = player_name
    player.league_id = league_id
    player.team_id = team_id
    player.position = position or player.position or "UNK"
    return player


def _upsert_game(
    db: Session,
    *,
    league_id: int,
    game_date,
    home_team_id: int,
    away_team_id: int,
    source_id: str,
    status: str = "unknown",
    home_team_external_id: Optional[str] = None,
    away_team_external_id: Optional[str] = None,
    source_updated_at: Optional[datetime] = None,
    raw_schedule_payload: Optional[dict[str, Any]] = None,
) -> Game:
    season = season_from_date(game_date)
    game = db.execute(
        select(Game).where(Game.source_system == NBA_SOURCE_SYSTEM, Game.source_id == source_id)
    ).scalar_one_or_none()
    if game is None:
        game = Game(
            league_id=league_id,
            game_date=game_date,
            season=season,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            source_system=NBA_SOURCE_SYSTEM,
            source_id=source_id,
            external_game_id=source_id,
            status=status,
            home_team_external_id=home_team_external_id,
            away_team_external_id=away_team_external_id,
            source_updated_at=source_updated_at,
            raw_schedule_payload=json.dumps(raw_schedule_payload) if raw_schedule_payload is not None else None,
        )
        db.add(game)
        db.flush()
        return game

    game.league_id = league_id
    game.game_date = game_date
    game.season = season
    game.home_team_id = home_team_id
    game.away_team_id = away_team_id
    game.external_game_id = source_id
    game.status = status
    game.home_team_external_id = home_team_external_id
    game.away_team_external_id = away_team_external_id
    game.source_updated_at = source_updated_at
    if raw_schedule_payload is not None:
        game.raw_schedule_payload = json.dumps(raw_schedule_payload)
    return game


def _parse_minutes(raw: Any) -> Optional[float]:
    if raw is None or raw in ("", "0", "0:00"):
        return None
    s = str(raw)
    if ":" in s:
        parts = s.split(":")
        try:
            return round(int(parts[0]) + int(parts[1]) / 60, 2)
        except (ValueError, IndexError):
            return None
    try:
        return float(s)
    except ValueError:
        return None


def _matchup_side(matchup: str) -> str:
    return "home" if "vs." in matchup else "away"


def _team_stat_exists(db: Session, *, source_game_id: str, source_team_id: str) -> bool:
    return db.execute(
        select(TeamGameStat.id).where(
            TeamGameStat.source_system == NBA_SOURCE_SYSTEM,
            TeamGameStat.source_game_id == source_game_id,
            TeamGameStat.source_team_id == source_team_id,
        )
    ).scalar_one_or_none() is not None


def _get_existing_team_stat(db: Session, *, source_game_id: str, source_team_id: str) -> Optional[TeamGameStat]:
    return db.execute(
        select(TeamGameStat).where(
            TeamGameStat.source_system == NBA_SOURCE_SYSTEM,
            TeamGameStat.source_game_id == source_game_id,
            TeamGameStat.source_team_id == source_team_id,
        )
    ).scalar_one_or_none()


def _clear_existing_nba_data(db: Session, *, clear_since=None) -> None:
    """Clear NBA data before reload.

    clear_since=None: full wipe (league/teams/players/games). Used on first-ever ingest.
    clear_since=date: partial wipe — only games on or after that date, preserving prior
                      seasons loaded by backfill. League, teams, and players are kept.
    """
    from datetime import date as date_type
    nba_league = db.execute(select(League).where(League.name == "NBA")).scalar_one_or_none()
    if nba_league is None:
        return

    if clear_since is None:
        nba_game_ids = select(Game.id).where(Game.league_id == nba_league.id)
        nba_player_ids = select(Player.id).where(Player.league_id == nba_league.id)
        db.execute(delete(Shyft).where(Shyft.league_id == nba_league.id))
        db.execute(
            delete(RollingMetricBaselineSample).where(
                RollingMetricBaselineSample.rolling_metric_id.in_(
                    select(RollingMetric.id).where(RollingMetric.player_id.in_(nba_player_ids))
                )
            )
        )
        db.execute(delete(RollingMetric).where(RollingMetric.player_id.in_(nba_player_ids)))
        db.execute(delete(PlayerGameStat).where(PlayerGameStat.game_id.in_(nba_game_ids)))
        db.execute(delete(TeamGameStat).where(TeamGameStat.game_id.in_(nba_game_ids)))
        db.execute(delete(Game).where(Game.league_id == nba_league.id))
        db.execute(delete(Player).where(Player.league_id == nba_league.id))
        db.execute(delete(Team).where(Team.league_id == nba_league.id))
        db.execute(delete(League).where(League.id == nba_league.id))
    else:
        # Partial wipe: clear only recent games and their dependent rows.
        # Historical backfill data (older than clear_since) is preserved.
        recent_game_ids = select(Game.id).where(
            Game.league_id == nba_league.id,
            Game.game_date >= clear_since,
        )
        recent_rolling_ids = select(RollingMetric.id).where(
            RollingMetric.game_id.in_(recent_game_ids)
        )
        db.execute(delete(Shyft).where(Shyft.game_id.in_(recent_game_ids)))
        db.execute(delete(RollingMetricBaselineSample).where(
            RollingMetricBaselineSample.rolling_metric_id.in_(recent_rolling_ids)
        ))
        db.execute(delete(RollingMetric).where(RollingMetric.game_id.in_(recent_game_ids)))
        db.execute(delete(PlayerGameStat).where(PlayerGameStat.game_id.in_(recent_game_ids)))
        db.execute(delete(TeamGameStat).where(TeamGameStat.game_id.in_(recent_game_ids)))
        db.execute(delete(Game).where(
            Game.league_id == nba_league.id,
            Game.game_date >= clear_since,
        ))
        # League, teams, and players are shared across seasons — keep them.
    db.flush()


def load_nba_snapshot(db: Session, *, snapshot_dir: Optional[Path] = None, clear_since=None) -> LoadResult:
    snapshot_dir = _resolve_snapshot_dir(snapshot_dir)
    manifest = _read_json(snapshot_dir / "manifest.json")
    league_game_log = _read_json(snapshot_dir / "leaguegamelog.json")
    common_all_players = _read_json(snapshot_dir / "commonallplayers.json")

    league_rows = _to_rows(league_game_log, "LeagueGameLog")
    player_rows = _to_rows(common_all_players, "CommonAllPlayers")
    players_by_id = {str(row["PERSON_ID"]): row for row in player_rows}

    roster_positions: dict[str, str] = {}
    for roster_path in sorted((snapshot_dir / "rosters").glob("*.json")):
        roster_payload = _read_json(roster_path)
        for row in _to_rows(roster_payload, "CommonTeamRoster"):
            roster_positions[str(row["PLAYER_ID"])] = row.get("POSITION") or "UNK"

    _clear_existing_nba_data(db, clear_since=clear_since)

    # Get-or-create: full wipe deletes the league so it won't exist; partial wipe keeps it.
    league = db.execute(select(League).where(League.name == "NBA")).scalar_one_or_none()
    if league is None:
        league = League(name="NBA")
        db.add(league)
        db.flush()

    game_rows_by_id: dict[str, list[dict[str, Any]]] = {}
    for row in league_rows:
        game_rows_by_id.setdefault(str(row["GAME_ID"]), []).append(row)

    team_cache: dict[str, Team] = {}
    game_cache: dict[str, Game] = {}
    player_cache: dict[str, Player] = {}

    for game_id in manifest["game_ids"]:
        rows = game_rows_by_id.get(str(game_id), [])
        if len(rows) != 2:
            continue

        home_row = next((row for row in rows if _matchup_side(row["MATCHUP"]) == "home"), None)
        away_row = next((row for row in rows if _matchup_side(row["MATCHUP"]) == "away"), None)
        if home_row is None or away_row is None:
            continue

        for row in rows:
            team_key = str(row["TEAM_ID"])
            if team_key not in team_cache:
                team_cache[team_key] = _upsert_team(
                    db,
                    league_id=league.id,
                    team_name=row["TEAM_NAME"],
                    source_id=team_key,
                )

        game_cache[str(game_id)] = _upsert_game(
            db,
            league_id=league.id,
            game_date=datetime.strptime(home_row["GAME_DATE"], "%Y-%m-%dT%H:%M:%S").date()
            if "T" in home_row["GAME_DATE"]
            else datetime.strptime(home_row["GAME_DATE"], "%Y-%m-%d").date(),
            home_team_id=team_cache[str(home_row["TEAM_ID"])].id,
            away_team_id=team_cache[str(away_row["TEAM_ID"])].id,
            source_id=str(game_id),
        )

    stats_loaded = 0
    team_stats_loaded = 0
    skipped_stat_rows = 0
    for game_id in manifest["game_ids"]:
        game = game_cache.get(str(game_id))
        traditional_path = snapshot_dir / "games" / f"{game_id}_traditional.json"
        advanced_path = snapshot_dir / "games" / f"{game_id}_advanced.json"
        usage_path = snapshot_dir / "games" / f"{game_id}_usage.json"
        if game is None or not traditional_path.exists():
            continue

        traditional_payload = _read_json(traditional_path)
        advanced_payload = _read_json(advanced_path) if advanced_path.exists() else None
        traditional_rows = _to_rows(traditional_payload, "PlayerStats")
        team_rows = _optional_rows(traditional_payload, "TeamStats")
        advanced_team_rows = _optional_rows(advanced_payload, "TeamStats")
        usage_rows = _optional_rows(_read_json(usage_path) if usage_path.exists() else None, "sqlPlayersUsage")
        usage_by_player_id = {str(row["PLAYER_ID"]): row for row in usage_rows}
        advanced_by_team_id = {str(row["TEAM_ID"]): row for row in advanced_team_rows}

        for raw_record_index, row in enumerate(team_rows):
            team_key = str(row.get("TEAM_ID", ""))
            team = team_cache.get(team_key)
            if team is None:
                skipped_stat_rows += 1
                continue

            advanced_row = advanced_by_team_id.get(team_key)
            required_values = [
                row.get("PTS"),
                row.get("REB"),
                row.get("AST"),
                row.get("FG_PCT"),
                row.get("FG3_PCT"),
                row.get("TO"),
            ]
            if any(value is None for value in required_values):
                skipped_stat_rows += 1
                continue

            is_home = team.id == game.home_team_id
            opponent_team_id = game.away_team_id if is_home else game.home_team_id
            opponent_team = next((cached_team for cached_team in team_cache.values() if cached_team.id == opponent_team_id), None)

            db.add(
                TeamGameStat(
                    team_id=team.id,
                    game_id=game.id,
                    opponent_team_id=opponent_team_id,
                    opponent_name=opponent_team.name if opponent_team is not None else None,
                    home_away="vs" if is_home else "@",
                    points=row.get("PTS"),
                    rebounds=row.get("REB"),
                    assists=row.get("AST"),
                    fg_pct=row.get("FG_PCT"),
                    fg3_pct=row.get("FG3_PCT"),
                    turnovers=row.get("TO"),
                    pace=advanced_row.get("PACE") if advanced_row else None,
                    off_rating=advanced_row.get("OFF_RATING") if advanced_row else None,
                    source_system=NBA_SOURCE_SYSTEM,
                    source_game_id=str(game_id),
                    source_team_id=team_key,
                    raw_snapshot_path=str(snapshot_dir),
                    raw_traditional_payload_path=str(traditional_path),
                    raw_advanced_payload_path=str(advanced_path) if advanced_path.exists() else None,
                    raw_record_index=raw_record_index,
                )
            )
            team_stats_loaded += 1

        for raw_record_index, row in enumerate(traditional_rows):
            player_id = str(row["PLAYER_ID"])
            if row.get("MIN") in (None, "", "0", "0:00"):
                skipped_stat_rows += 1
                continue

            player_info = players_by_id.get(player_id)
            team_key = str(row["TEAM_ID"])
            if player_info is None or team_key not in team_cache:
                skipped_stat_rows += 1
                continue

            player = player_cache.get(player_id)
            if player is None:
                player = _upsert_player(
                    db,
                    league_id=league.id,
                    team_id=team_cache[team_key].id,
                    player_name=row["PLAYER_NAME"],
                    position=roster_positions.get(player_id) or row.get("START_POSITION") or "UNK",
                    source_id=player_id,
                )
                player_cache[player_id] = player
            else:
                player.team_id = team_cache[team_key].id

            usage_row = usage_by_player_id.get(player_id, {})
            db.add(
                PlayerGameStat(
                    player_id=player.id,
                    game_id=game.id,
                    points=row.get("PTS"),
                    rebounds=row.get("REB"),
                    assists=row.get("AST"),
                    steals=row.get("STL"),
                    blocks=row.get("BLK"),
                    turnovers=row.get("TO"),
                    minutes_played=_parse_minutes(row.get("MIN")),
                    plus_minus=row.get("PLUS_MINUS"),
                    fg_pct=row.get("FG_PCT"),
                    fg3_pct=row.get("FG3_PCT"),
                    ft_pct=row.get("FT_PCT"),
                    usage_rate=usage_row.get("USG_PCT"),
                    source_system=NBA_SOURCE_SYSTEM,
                    source_game_id=str(game_id),
                    source_player_id=player_id,
                    raw_snapshot_path=str(snapshot_dir),
                    raw_payload_path=str(traditional_path),
                    raw_record_index=raw_record_index,
                )
            )
            stats_loaded += 1

    db.commit()
    return LoadResult(
        snapshot_dir=snapshot_dir,
        teams_loaded=len(team_cache),
        players_loaded=len(player_cache),
        games_loaded=len(game_cache),
        stats_loaded=stats_loaded,
        team_stats_loaded=team_stats_loaded,
        skipped_stat_rows=skipped_stat_rows,
        affected_player_ids=[p.id for p in player_cache.values()],
        affected_team_ids=[team.id for team in team_cache.values()],
        affected_game_ids=[game.id for game in game_cache.values()],
    )


def _get_or_create_nba_league(db: Session) -> League:
    league = db.execute(select(League).where(League.name == "NBA")).scalar_one_or_none()
    if league is None:
        league = League(name="NBA")
        db.add(league)
        db.flush()
    return league


def _get_existing_player_stat(db: Session, *, source_game_id: str, source_player_id: str) -> Optional[PlayerGameStat]:
    return db.execute(
        select(PlayerGameStat).where(
            PlayerGameStat.source_system == NBA_SOURCE_SYSTEM,
            PlayerGameStat.source_game_id == source_game_id,
            PlayerGameStat.source_player_id == source_player_id,
        )
    ).scalar_one_or_none()


def load_nba_games_incremental(
    db: Session,
    *,
    game_payloads: list[dict],
) -> LoadResult:
    """Normalize and upsert NBA game data without wiping existing records.

    Called by the incremental ingest path (via NBASAPISource.load_events) and
    suitable for processing individual events from a future Kafka stream consumer.

    Idempotency: player_game_stats and team_game_stats rows are skipped if the
    source game/entity pair already exists in the DB — enforced both by DB
    constraints and the pre-checks here to avoid constraint-error noise on
    expected duplicates.

    Future Kafka consumer plug-in point:
        A stream consumer calls this function with game_payloads=[message.value]
        for each Kafka message it consumes. Normalization and idempotency behavior
        are identical to the batch API path.

    Args:
        game_payloads: list of raw payload dicts from IngestEvent.raw_payload.
                       Each dict contains keys: game_id, snapshot_dir, traditional,
                       advanced, usage.
    """
    league = _get_or_create_nba_league(db)

    team_cache: dict[str, Team] = {}
    game_cache: dict[str, Game] = {}
    player_cache: dict[str, Player] = {}

    stats_loaded = 0
    team_stats_loaded = 0
    skipped_stat_rows = 0

    for payload in game_payloads:
        game_id = str(payload["game_id"])
        snapshot_dir_str = payload.get("snapshot_dir", "")
        traditional_data = payload["traditional"]
        advanced_data = payload.get("advanced")
        usage_data = payload.get("usage")

        traditional_rows = _to_rows(traditional_data, "PlayerStats")
        team_rows = _optional_rows(traditional_data, "TeamStats")
        advanced_rows = _optional_rows(advanced_data, "TeamStats")
        usage_rows = _optional_rows(usage_data, "sqlPlayersUsage")
        usage_by_player_id = {str(row["PLAYER_ID"]): row for row in usage_rows}
        advanced_by_team_id = {str(row["TEAM_ID"]): row for row in advanced_rows}

        if not traditional_rows:
            continue

        # Derive game metadata from boxscore rows (home team identified by matchup "vs.").
        # Playoff boxscores omit MATCHUP and GAME_DATE from PlayerStats; fall back to
        # game_log_meta supplied by the ingest source when those fields are absent.
        game_log_meta = payload.get("game_log_meta") or {}
        home_row: Optional[dict[str, Any]] = None
        away_row: Optional[dict[str, Any]] = None
        teams_in_game: dict[str, dict] = {}
        for row in traditional_rows:
            team_key = str(row.get("TEAM_ID", ""))
            if team_key and team_key not in teams_in_game:
                teams_in_game[team_key] = row
            matchup = row.get("MATCHUP") or ""
            if "vs." in matchup and home_row is None:
                home_row = row
            elif "@" in matchup and away_row is None:
                away_row = row

        # Fallback: use leaguegamelog metadata when boxscore rows lack MATCHUP/GAME_DATE.
        if (home_row is None or away_row is None) and game_log_meta:
            home_tid = str(game_log_meta.get("home_team_id") or "")
            away_tid = str(game_log_meta.get("away_team_id") or "")
            for row in traditional_rows:
                team_key = str(row.get("TEAM_ID", ""))
                if team_key == home_tid and home_row is None:
                    home_row = {**row, "GAME_DATE": game_log_meta.get("game_date")}
                elif team_key == away_tid and away_row is None:
                    away_row = {**row, "GAME_DATE": game_log_meta.get("game_date")}

        # Build full team name lookup from TeamStats (present in all game types).
        # Playoff PlayerStats omits TEAM_NAME; TeamStats has it but as just the nickname
        # ("Knicks"), while regular season has the full name ("New York Knicks").
        # Combine TEAM_CITY + TEAM_NAME when the city isn't already part of the name.
        team_name_by_id: dict[str, str] = {}
        for tr in team_rows:
            tid = str(tr.get("TEAM_ID", ""))
            city = tr.get("TEAM_CITY") or ""
            name = tr.get("TEAM_NAME") or ""
            if name and city and city not in name:
                team_name_by_id[tid] = f"{city} {name}"
            elif name:
                team_name_by_id[tid] = name
            elif city:
                team_name_by_id[tid] = f"{city} {tr.get('TEAM_ABBREVIATION', tid)}".strip()

        for team_key, sample_row in teams_in_game.items():
            if team_key not in team_cache:
                team_name = (
                    sample_row.get("TEAM_NAME")
                    or team_name_by_id.get(team_key)
                    or f"Team {team_key}"
                )
                team_cache[team_key] = _upsert_team(
                    db,
                    league_id=league.id,
                    team_name=team_name,
                    source_id=team_key,
                )

        if home_row and away_row:
            home_team_id = team_cache.get(str(home_row["TEAM_ID"]))
            away_team_id = team_cache.get(str(away_row["TEAM_ID"]))
            game_date_raw = home_row.get("GAME_DATE") or ""
            if home_team_id and away_team_id and game_date_raw:
                game_date = (
                    datetime.strptime(game_date_raw, "%Y-%m-%dT%H:%M:%S").date()
                    if "T" in game_date_raw
                    else datetime.strptime(game_date_raw, "%Y-%m-%d").date()
                )
                game_cache[game_id] = _upsert_game(
                    db,
                    league_id=league.id,
                    game_date=game_date,
                    home_team_id=home_team_id.id,
                    away_team_id=away_team_id.id,
                    source_id=game_id,
                )

        game = game_cache.get(game_id)
        if game is None:
            skipped_stat_rows += len(traditional_rows)
            continue

        traditional_path_str = f"{snapshot_dir_str}/games/{game_id}_traditional.json"
        advanced_path_str = f"{snapshot_dir_str}/games/{game_id}_advanced.json" if snapshot_dir_str else ""

        for raw_record_index, row in enumerate(team_rows):
            source_team_id = str(row.get("TEAM_ID", ""))
            if not source_team_id:
                skipped_stat_rows += 1
                continue

            team = team_cache.get(source_team_id)
            if team is None:
                skipped_stat_rows += 1
                continue

            advanced_row = advanced_by_team_id.get(source_team_id)
            required_values = [
                row.get("PTS"),
                row.get("REB"),
                row.get("AST"),
                row.get("FG_PCT"),
                row.get("FG3_PCT"),
                row.get("TO"),
            ]
            if any(value is None for value in required_values):
                skipped_stat_rows += 1
                continue

            is_home = team.id == game.home_team_id
            opponent_team_id = game.away_team_id if is_home else game.home_team_id
            opponent_team = next((cached_team for cached_team in team_cache.values() if cached_team.id == opponent_team_id), None)

            existing_team_stat = _get_existing_team_stat(db, source_game_id=game_id, source_team_id=source_team_id)
            if existing_team_stat is None:
                db.add(
                    TeamGameStat(
                        team_id=team.id,
                        game_id=game.id,
                        opponent_team_id=opponent_team_id,
                        opponent_name=opponent_team.name if opponent_team is not None else None,
                        home_away="vs" if is_home else "@",
                        points=row.get("PTS"),
                        rebounds=row.get("REB"),
                        assists=row.get("AST"),
                        fg_pct=row.get("FG_PCT"),
                        fg3_pct=row.get("FG3_PCT"),
                        turnovers=row.get("TO"),
                        pace=advanced_row.get("PACE") if advanced_row else None,
                        off_rating=advanced_row.get("OFF_RATING") if advanced_row else None,
                        source_system=NBA_SOURCE_SYSTEM,
                        source_game_id=game_id,
                        source_team_id=source_team_id,
                        raw_snapshot_path=snapshot_dir_str or None,
                        raw_traditional_payload_path=traditional_path_str or None,
                        raw_advanced_payload_path=advanced_path_str or None,
                        raw_record_index=raw_record_index,
                    )
                )
                team_stats_loaded += 1
            else:
                existing_team_stat.team_id = team.id
                existing_team_stat.game_id = game.id
                existing_team_stat.opponent_team_id = opponent_team_id
                existing_team_stat.opponent_name = opponent_team.name if opponent_team is not None else None
                existing_team_stat.home_away = "vs" if is_home else "@"
                existing_team_stat.points = row.get("PTS")
                existing_team_stat.rebounds = row.get("REB")
                existing_team_stat.assists = row.get("AST")
                existing_team_stat.fg_pct = row.get("FG_PCT")
                existing_team_stat.fg3_pct = row.get("FG3_PCT")
                existing_team_stat.turnovers = row.get("TO")
                existing_team_stat.pace = advanced_row.get("PACE") if advanced_row else None
                existing_team_stat.off_rating = advanced_row.get("OFF_RATING") if advanced_row else None
                existing_team_stat.raw_snapshot_path = snapshot_dir_str or None
                existing_team_stat.raw_traditional_payload_path = traditional_path_str or None
                existing_team_stat.raw_advanced_payload_path = advanced_path_str or None
                existing_team_stat.raw_record_index = raw_record_index

        for raw_record_index, row in enumerate(traditional_rows):
            source_player_id = str(row["PLAYER_ID"])

            if row.get("MIN") in (None, "", "0", "0:00"):
                skipped_stat_rows += 1
                continue

            team_key = str(row.get("TEAM_ID", ""))
            if team_key not in team_cache:
                skipped_stat_rows += 1
                continue

            player = player_cache.get(source_player_id)
            if player is None:
                player = _upsert_player(
                    db,
                    league_id=league.id,
                    team_id=team_cache[team_key].id,
                    player_name=row["PLAYER_NAME"],
                    position=row.get("START_POSITION") or "UNK",
                    source_id=source_player_id,
                )
                player_cache[source_player_id] = player
            else:
                player.team_id = team_cache[team_key].id

            usage_row = usage_by_player_id.get(source_player_id, {})
            existing_stat = _get_existing_player_stat(db, source_game_id=game_id, source_player_id=source_player_id)
            if existing_stat is None:
                db.add(
                    PlayerGameStat(
                        player_id=player.id,
                        game_id=game.id,
                        points=row.get("PTS"),
                        rebounds=row.get("REB"),
                        assists=row.get("AST"),
                        steals=row.get("STL"),
                        blocks=row.get("BLK"),
                        turnovers=row.get("TO"),
                        minutes_played=_parse_minutes(row.get("MIN")),
                        plus_minus=row.get("PLUS_MINUS"),
                        fg_pct=row.get("FG_PCT"),
                        fg3_pct=row.get("FG3_PCT"),
                        ft_pct=row.get("FT_PCT"),
                        usage_rate=usage_row.get("USG_PCT"),
                        source_system=NBA_SOURCE_SYSTEM,
                        source_game_id=game_id,
                        source_player_id=source_player_id,
                        raw_snapshot_path=snapshot_dir_str,
                        raw_payload_path=traditional_path_str,
                        raw_record_index=raw_record_index,
                    )
                )
                stats_loaded += 1
            else:
                existing_stat.player_id = player.id
                existing_stat.game_id = game.id
                existing_stat.points = row.get("PTS")
                existing_stat.rebounds = row.get("REB")
                existing_stat.assists = row.get("AST")
                existing_stat.steals = row.get("STL")
                existing_stat.blocks = row.get("BLK")
                existing_stat.turnovers = row.get("TO")
                existing_stat.minutes_played = _parse_minutes(row.get("MIN"))
                existing_stat.plus_minus = row.get("PLUS_MINUS")
                existing_stat.fg_pct = row.get("FG_PCT")
                existing_stat.fg3_pct = row.get("FG3_PCT")
                existing_stat.ft_pct = row.get("FT_PCT")
                existing_stat.usage_rate = usage_row.get("USG_PCT")
                existing_stat.raw_snapshot_path = snapshot_dir_str
                existing_stat.raw_payload_path = traditional_path_str
                existing_stat.raw_record_index = raw_record_index

    db.flush()

    # Refresh opponent_name for all team_game_stats that reference teams processed
    # this session. Fixes rows written before team names were resolved correctly
    # (e.g. when playoff boxscores caused "Team 1610612752" to be stored).
    if team_cache:
        db.execute(
            update(TeamGameStat)
            .where(
                TeamGameStat.source_system == NBA_SOURCE_SYSTEM,
                TeamGameStat.opponent_team_id.in_([t.id for t in team_cache.values()]),
            )
            .values(
                opponent_name=(
                    select(Team.name)
                    .where(Team.id == TeamGameStat.opponent_team_id)
                    .correlate(TeamGameStat)
                    .scalar_subquery()
                )
            )
        )

    return LoadResult(
        snapshot_dir=None,
        teams_loaded=len(team_cache),
        players_loaded=len(player_cache),
        games_loaded=len(game_cache),
        stats_loaded=stats_loaded,
        team_stats_loaded=team_stats_loaded,
        skipped_stat_rows=skipped_stat_rows,
        affected_player_ids=[p.id for p in player_cache.values()],
        affected_team_ids=[team.id for team in team_cache.values()],
        affected_game_ids=[game.id for game in game_cache.values()],
    )
