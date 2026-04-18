from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
import json
from pathlib import Path
from typing import Any, Optional

from sqlalchemy import delete, select
from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.league import League
from app.models.player import Player
from app.models.player_game_stat import PlayerGameStat
from app.models.rolling_metric import RollingMetric
from app.models.rolling_metric_baseline_sample import RollingMetricBaselineSample
from app.models.signal import Signal
from app.models.team import Team
from app.services.nba_ingest_service import NBA_SOURCE_SYSTEM, raw_nba_root


@dataclass(frozen=True)
class LoadResult:
    snapshot_dir: Path
    teams_loaded: int
    players_loaded: int
    games_loaded: int
    stats_loaded: int
    skipped_stat_rows: int


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
) -> Game:
    game = db.execute(
        select(Game).where(Game.source_system == NBA_SOURCE_SYSTEM, Game.source_id == source_id)
    ).scalar_one_or_none()
    if game is None:
        game = Game(
            league_id=league_id,
            game_date=game_date,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            source_system=NBA_SOURCE_SYSTEM,
            source_id=source_id,
        )
        db.add(game)
        db.flush()
        return game

    game.league_id = league_id
    game.game_date = game_date
    game.home_team_id = home_team_id
    game.away_team_id = away_team_id
    return game


def _matchup_side(matchup: str) -> str:
    return "home" if "vs." in matchup else "away"


def _clear_existing_nba_data(db: Session) -> None:
    nba_league = db.execute(select(League).where(League.name == "NBA")).scalar_one_or_none()
    if nba_league is None:
        return

    nba_game_ids = select(Game.id).where(Game.league_id == nba_league.id)
    nba_player_ids = select(Player.id).where(Player.league_id == nba_league.id)
    db.execute(delete(Signal).where(Signal.league_id == nba_league.id))
    db.execute(
        delete(RollingMetricBaselineSample).where(
            RollingMetricBaselineSample.rolling_metric_id.in_(
                select(RollingMetric.id).where(RollingMetric.player_id.in_(nba_player_ids))
            )
        )
    )
    db.execute(delete(RollingMetric).where(RollingMetric.player_id.in_(nba_player_ids)))
    db.execute(delete(PlayerGameStat).where(PlayerGameStat.game_id.in_(nba_game_ids)))
    db.execute(delete(Game).where(Game.league_id == nba_league.id))
    db.execute(delete(Player).where(Player.league_id == nba_league.id))
    db.execute(delete(Team).where(Team.league_id == nba_league.id))
    db.execute(delete(League).where(League.id == nba_league.id))
    db.flush()


def load_nba_snapshot(db: Session, *, snapshot_dir: Optional[Path] = None) -> LoadResult:
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

    _clear_existing_nba_data(db)
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
    skipped_stat_rows = 0
    for game_id in manifest["game_ids"]:
        game = game_cache.get(str(game_id))
        traditional_path = snapshot_dir / "games" / f"{game_id}_traditional.json"
        usage_path = snapshot_dir / "games" / f"{game_id}_usage.json"
        if game is None or not traditional_path.exists() or not usage_path.exists():
            continue

        traditional_rows = _to_rows(_read_json(traditional_path), "PlayerStats")
        usage_rows = _to_rows(_read_json(usage_path), "sqlPlayersUsage")
        usage_by_player_id = {str(row["PLAYER_ID"]): row for row in usage_rows}

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
        skipped_stat_rows=skipped_stat_rows,
    )
