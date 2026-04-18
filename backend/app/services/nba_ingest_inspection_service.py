from __future__ import annotations

from pathlib import Path
from typing import Any, Optional

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.game import Game
from app.models.league import League
from app.models.player import Player
from app.models.player_game_stat import PlayerGameStat
from app.models.team import Team
from app.services.nba_ingest_service import NBA_SOURCE_SYSTEM, raw_nba_root


def _latest_snapshot_dir() -> Optional[Path]:
    latest_path = raw_nba_root() / "LATEST"
    if not latest_path.exists():
        return None
    return Path(latest_path.read_text(encoding="utf-8").strip())


def get_ingest_summary(db: Session) -> dict[str, Any]:
    nba_league = db.execute(select(League).where(League.name == "NBA")).scalar_one_or_none()
    if nba_league is None:
        return {"league": "NBA", "games": 0, "players": 0, "stats": 0, "latest_snapshot_dir": None}

    game_count = db.execute(select(func.count()).select_from(Game).where(Game.league_id == nba_league.id)).scalar_one()
    player_count = db.execute(select(func.count()).select_from(Player).where(Player.league_id == nba_league.id)).scalar_one()
    stat_count = db.execute(
        select(func.count())
        .select_from(PlayerGameStat)
        .join(Game, PlayerGameStat.game_id == Game.id)
        .where(Game.league_id == nba_league.id)
    ).scalar_one()
    latest_snapshot_dir = _latest_snapshot_dir()
    return {
        "league": "NBA",
        "games": game_count,
        "players": player_count,
        "stats": stat_count,
        "latest_snapshot_dir": str(latest_snapshot_dir) if latest_snapshot_dir else None,
    }


def list_recent_nba_games(db: Session, limit: int = 10) -> list[dict[str, Any]]:
    away_teams = Team.__table__.alias("away_teams")
    rows = db.execute(
        select(Game.id, Game.game_date, Game.source_id, Team.name, away_teams.c.name)
        .join(League, Game.league_id == League.id)
        .join(Team, Game.home_team_id == Team.id)
        .join(away_teams, Game.away_team_id == away_teams.c.id)
        .where(League.name == "NBA")
        .order_by(Game.game_date.desc(), Game.id.desc())
        .limit(limit)
    ).all()
    snapshot_dir = _latest_snapshot_dir()
    results = []
    for game_id, game_date, source_id, home_team_name, away_team_name in rows:
        results.append(
            {
                "game_id": game_id,
                "game_date": str(game_date),
                "source_system": NBA_SOURCE_SYSTEM,
                "source_id": source_id,
                "home_team": home_team_name,
                "away_team": away_team_name,
                "traditional_payload_path": str(snapshot_dir / "games" / f"{source_id}_traditional.json") if snapshot_dir else None,
                "usage_payload_path": str(snapshot_dir / "games" / f"{source_id}_usage.json") if snapshot_dir else None,
            }
        )
    return results


def list_recent_nba_players(db: Session, limit: int = 20) -> list[dict[str, Any]]:
    rows = db.execute(
        select(Player.id, Player.name, Player.position, Team.name, Player.source_id, func.count(PlayerGameStat.id))
        .join(League, Player.league_id == League.id)
        .join(Team, Player.team_id == Team.id)
        .outerjoin(PlayerGameStat, PlayerGameStat.player_id == Player.id)
        .where(League.name == "NBA")
        .group_by(Player.id, Team.name)
        .order_by(func.count(PlayerGameStat.id).desc(), Player.name.asc())
        .limit(limit)
    ).all()
    return [
        {
            "player_id": player_id,
            "name": name,
            "position": position,
            "team_name": team_name,
            "source_system": NBA_SOURCE_SYSTEM,
            "source_id": source_id,
            "games_loaded": game_count,
        }
        for player_id, name, position, team_name, source_id, game_count in rows
    ]
