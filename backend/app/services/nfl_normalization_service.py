from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.league import League
from app.models.player import Player
from app.models.player_game_stat import PlayerGameStat
from app.models.team import Team
from app.models.team_game_stat import TeamGameStat
from app.services.nfl_ingest_service import NFL_SOURCE_SYSTEM


@dataclass
class NFLLoadResult:
    teams_loaded: int
    players_loaded: int
    games_loaded: int
    stats_loaded: int
    skipped_stat_rows: int
    affected_player_ids: list[int] = field(default_factory=list)
    affected_team_ids: list[int] = field(default_factory=list)
    affected_game_ids: list[int] = field(default_factory=list)


def _parse_game_date(raw: Any) -> datetime.date:
    value = str(raw or "").strip()
    if not value:
        raise ValueError("NFL game payload is missing a date")
    normalized = value.replace("Z", "+00:00")
    return datetime.fromisoformat(normalized).date()


def _coalesce_boxscore_game(boxscore: dict[str, Any]) -> dict[str, Any]:
    nested = boxscore.get("Score")
    if isinstance(nested, dict):
        merged = dict(boxscore)
        merged.update({key: value for key, value in nested.items() if key not in merged or merged[key] in (None, "")})
        return merged
    return boxscore


def _coalesce_rows(boxscore: dict[str, Any], *keys: str) -> list[dict[str, Any]]:
    for key in keys:
        rows = boxscore.get(key)
        if isinstance(rows, list):
            return [row for row in rows if isinstance(row, dict)]
    nested = boxscore.get("Score")
    if isinstance(nested, dict):
        for key in keys:
            rows = nested.get(key)
            if isinstance(rows, list):
                return [row for row in rows if isinstance(row, dict)]
    return []


def _get_or_create_league(db: Session) -> League:
    league = db.execute(select(League).where(League.name == "NFL")).scalar_one_or_none()
    if league is None:
        league = League(name="NFL")
        db.add(league)
        db.flush()
    return league


def _upsert_team(
    db: Session,
    *,
    league_id: int,
    source_id: str,
    team_name: str,
) -> Team:
    team = db.execute(
        select(Team).where(Team.source_system == NFL_SOURCE_SYSTEM, Team.source_id == source_id)
    ).scalar_one_or_none()
    if team is None:
        team = Team(
            name=team_name,
            league_id=league_id,
            source_system=NFL_SOURCE_SYSTEM,
            source_id=source_id,
        )
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
    source_id: str,
    player_name: str,
    position: str,
) -> Player:
    player = db.execute(
        select(Player).where(Player.source_system == NFL_SOURCE_SYSTEM, Player.source_id == source_id)
    ).scalar_one_or_none()
    if player is None:
        player = Player(
            name=player_name,
            league_id=league_id,
            team_id=team_id,
            position=position or "UNK",
            source_system=NFL_SOURCE_SYSTEM,
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
    source_id: str,
    game_date,
    season: Optional[str],
    home_team_id: int,
    away_team_id: int,
) -> Game:
    game = db.execute(
        select(Game).where(Game.source_system == NFL_SOURCE_SYSTEM, Game.source_id == source_id)
    ).scalar_one_or_none()
    if game is None:
        game = Game(
            league_id=league_id,
            game_date=game_date,
            season=season,
            home_team_id=home_team_id,
            away_team_id=away_team_id,
            source_system=NFL_SOURCE_SYSTEM,
            source_id=source_id,
        )
        db.add(game)
        db.flush()
        return game

    game.league_id = league_id
    game.game_date = game_date
    game.season = season
    game.home_team_id = home_team_id
    game.away_team_id = away_team_id
    return game


def _player_stat_exists(db: Session, *, source_game_id: str, source_player_id: str) -> bool:
    return db.execute(
        select(PlayerGameStat.id).where(
            PlayerGameStat.source_system == NFL_SOURCE_SYSTEM,
            PlayerGameStat.source_game_id == source_game_id,
            PlayerGameStat.source_player_id == source_player_id,
        )
    ).scalar_one_or_none() is not None


def _team_stat_exists(db: Session, *, source_game_id: str, source_team_id: str) -> bool:
    return db.execute(
        select(TeamGameStat.id).where(
            TeamGameStat.source_system == NFL_SOURCE_SYSTEM,
            TeamGameStat.source_game_id == source_game_id,
            TeamGameStat.source_team_id == source_team_id,
        )
    ).scalar_one_or_none() is not None


def _safe_int(value: Any) -> Optional[int]:
    if value in (None, ""):
        return None
    try:
        return int(float(str(value).replace(",", "")))
    except (TypeError, ValueError):
        return None


def _team_source_id(team_row: dict[str, Any]) -> Optional[str]:
    value = team_row.get("TeamID") or team_row.get("GlobalTeamID") or team_row.get("Key")
    return str(value) if value not in (None, "") else None


def _team_display_name(team_row: dict[str, Any]) -> str:
    return (
        team_row.get("FullName")
        or team_row.get("Name")
        or " ".join(part for part in [team_row.get("City"), team_row.get("Name")] if part)
        or str(team_row.get("Key") or "Unknown Team")
    )


def _touchdowns(row: dict[str, Any]) -> Optional[int]:
    direct = row.get("Touchdowns")
    if direct is not None:
        return int(direct)

    pieces = [
        row.get("PassingTouchdowns"),
        row.get("RushingTouchdowns"),
        row.get("ReceivingTouchdowns"),
    ]
    numeric = [int(value) for value in pieces if value not in (None, "")]
    if numeric:
        return sum(numeric)
    return None


def _should_keep_player_row(row: dict[str, Any]) -> bool:
    tracked_values = [
        row.get("PassingYards"),
        row.get("RushingYards"),
        row.get("ReceivingYards"),
        row.get("Touchdowns"),
        row.get("PassingTouchdowns"),
        row.get("RushingTouchdowns"),
        row.get("ReceivingTouchdowns"),
        row.get("PassingAttempts"),
        row.get("RushingAttempts"),
        row.get("Targets"),
        row.get("Receptions"),
    ]
    return any(value not in (None, "", 0) for value in tracked_values)


def load_nfl_boxscores_incremental(
    db: Session,
    *,
    teams_payload: list[dict[str, Any]],
    players_payload: list[dict[str, Any]],
    boxscore_payloads: list[dict[str, Any]],
) -> NFLLoadResult:
    league = _get_or_create_league(db)

    teams_by_key: dict[str, dict[str, Any]] = {}
    team_cache: dict[str, Team] = {}
    player_reference_by_id: dict[str, dict[str, Any]] = {}
    player_cache: dict[str, Player] = {}
    game_cache: dict[str, Game] = {}

    for team_row in teams_payload:
        source_id = _team_source_id(team_row)
        if source_id is None:
            continue
        team_name = _team_display_name(team_row)
        teams_by_key[str(team_row.get("Key") or source_id)] = team_row
        team_cache[source_id] = _upsert_team(db, league_id=league.id, source_id=source_id, team_name=team_name)

    for player_row in players_payload:
        player_id = player_row.get("PlayerID")
        if player_id in (None, ""):
            continue
        player_reference_by_id[str(player_id)] = player_row

    stats_loaded = 0
    skipped_stat_rows = 0

    for raw_boxscore in boxscore_payloads:
        boxscore = _coalesce_boxscore_game(raw_boxscore)
        source_game_id = str(boxscore.get("GameID") or boxscore.get("GlobalGameID") or boxscore.get("GameKey") or "")
        if not source_game_id:
            continue

        home_team_ref = boxscore.get("HomeTeamID") or boxscore.get("HomeTeamKey") or boxscore.get("HomeTeam")
        away_team_ref = boxscore.get("AwayTeamID") or boxscore.get("AwayTeamKey") or boxscore.get("AwayTeam")
        home_team = team_cache.get(str(home_team_ref))
        away_team = team_cache.get(str(away_team_ref))

        if home_team is None and str(boxscore.get("HomeTeam") or "") in teams_by_key:
            ref = teams_by_key[str(boxscore["HomeTeam"])]
            source_id = _team_source_id(ref)
            if source_id:
                home_team = team_cache.get(source_id) or _upsert_team(
                    db,
                    league_id=league.id,
                    source_id=source_id,
                    team_name=_team_display_name(ref),
                )
                team_cache[source_id] = home_team

        if away_team is None and str(boxscore.get("AwayTeam") or "") in teams_by_key:
            ref = teams_by_key[str(boxscore["AwayTeam"])]
            source_id = _team_source_id(ref)
            if source_id:
                away_team = team_cache.get(source_id) or _upsert_team(
                    db,
                    league_id=league.id,
                    source_id=source_id,
                    team_name=_team_display_name(ref),
                )
                team_cache[source_id] = away_team

        if home_team is None or away_team is None:
            continue

        season_value = boxscore.get("Season")
        season = str(season_value) if season_value not in (None, "") else None
        game = _upsert_game(
            db,
            league_id=league.id,
            source_id=source_game_id,
            game_date=_parse_game_date(boxscore.get("Date") or boxscore.get("DateTime") or boxscore.get("Day")),
            season=season,
            home_team_id=home_team.id,
            away_team_id=away_team.id,
        )
        game_cache[source_game_id] = game

        home_score = _safe_int(boxscore.get("HomeScore") or boxscore.get("HomeTeamScore"))
        away_score = _safe_int(boxscore.get("AwayScore") or boxscore.get("AwayTeamScore"))
        score_rows = [
            (home_team, away_team, "vs", home_score, str(home_team_ref)),
            (away_team, home_team, "@", away_score, str(away_team_ref)),
        ]
        for team, opponent, home_away, points, source_team_id in score_rows:
            if points is None or _team_stat_exists(db, source_game_id=source_game_id, source_team_id=source_team_id):
                continue
            db.add(
                TeamGameStat(
                    team_id=team.id,
                    game_id=game.id,
                    opponent_team_id=opponent.id,
                    opponent_name=opponent.name,
                    home_away=home_away,
                    points=points,
                    source_system=NFL_SOURCE_SYSTEM,
                    source_game_id=source_game_id,
                    source_team_id=source_team_id,
                )
            )

        player_rows = _coalesce_rows(boxscore, "PlayerGames", "PlayerGameStats", "PlayerStats")
        for raw_record_index, row in enumerate(player_rows):
            source_player_id = row.get("PlayerID")
            if source_player_id in (None, ""):
                skipped_stat_rows += 1
                continue
            source_player_id = str(source_player_id)

            if _player_stat_exists(db, source_game_id=source_game_id, source_player_id=source_player_id):
                skipped_stat_rows += 1
                continue

            if not _should_keep_player_row(row):
                skipped_stat_rows += 1
                continue

            player_reference = player_reference_by_id.get(source_player_id, {})
            team_ref = row.get("TeamID") or player_reference.get("TeamID") or player_reference.get("Team")
            player_team = team_cache.get(str(team_ref))
            if player_team is None and str(player_reference.get("Team") or "") in teams_by_key:
                ref = teams_by_key[str(player_reference["Team"])]
                source_id = _team_source_id(ref)
                if source_id:
                    player_team = team_cache.get(source_id)

            if player_team is None:
                skipped_stat_rows += 1
                continue

            player = player_cache.get(source_player_id)
            if player is None:
                player = _upsert_player(
                    db,
                    league_id=league.id,
                    team_id=player_team.id,
                    source_id=source_player_id,
                    player_name=(
                        row.get("Name")
                        or player_reference.get("Name")
                        or f"Player {source_player_id}"
                    ),
                    position=str(row.get("Position") or player_reference.get("Position") or "UNK"),
                )
                player_cache[source_player_id] = player
            else:
                player.team_id = player_team.id

            db.add(
                PlayerGameStat(
                    player_id=player.id,
                    game_id=game.id,
                    passing_yards=row.get("PassingYards"),
                    rushing_yards=row.get("RushingYards"),
                    receiving_yards=row.get("ReceivingYards"),
                    touchdowns=_touchdowns(row),
                    source_system=NFL_SOURCE_SYSTEM,
                    source_game_id=source_game_id,
                    source_player_id=source_player_id,
                    raw_record_index=raw_record_index,
                )
            )
            stats_loaded += 1

    db.flush()
    return NFLLoadResult(
        teams_loaded=len(team_cache),
        players_loaded=len(player_cache),
        games_loaded=len(game_cache),
        stats_loaded=stats_loaded,
        skipped_stat_rows=skipped_stat_rows,
        affected_player_ids=[player.id for player in player_cache.values()],
        affected_team_ids=[team.id for team in team_cache.values()],
        affected_game_ids=[game.id for game in game_cache.values()],
    )
