from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timedelta
import json
import logging
from typing import Optional

from sqlalchemy import select

from app.core.config import settings
from app.db.session import SessionLocal
from app.ingest.nba_schedule_provider import NBAScheduleProvider
from app.ingest.nfl_schedule_provider import NFLScheduleProvider
from app.ingest.providers import LeagueProvider, ProviderGame
from app.models.game import Game
from app.models.league import League
from app.models.sync_checkpoint import SyncCheckpoint
from app.models.team import Team
from app.services.nba_normalization_service import load_nba_games_incremental
from app.services.signal_generation_service import SignalGenerationResult, generate_signals_for_players

logger = logging.getLogger(__name__)


@dataclass(frozen=True)
class ScheduleSyncResult:
    league: str
    discovered_games: int = 0
    skipped_games: int = 0
    hydrated_games: int = 0
    players_loaded: int = 0
    team_stats_loaded: int = 0
    player_stats_loaded: int = 0
    signals_created: int = 0
    signals_updated: int = 0


def _get_provider(league: str) -> LeagueProvider:
    normalized = league.lower()
    if normalized == "nba":
        return NBAScheduleProvider()
    if normalized == "nfl":
        return NFLScheduleProvider()
    raise ValueError(f"Unsupported league: {league}")


def _get_or_create_league(db, name: str) -> League:
    league = db.execute(select(League).where(League.name == name.upper())).scalar_one_or_none()
    if league is None:
        league = League(name=name.upper())
        db.add(league)
        db.flush()
    return league


def _upsert_discovered_game(db, *, league_id: int, game: ProviderGame) -> Game:
    home_team = db.execute(
        select(Team).where(Team.league_id == league_id, Team.source_id == game.home_team_external_id)
    ).scalar_one_or_none()
    if home_team is None:
        home_team = Team(
            name=f"Team {game.home_team_external_id}",
            league_id=league_id,
            source_system=game.league,
            source_id=game.home_team_external_id,
        )
        db.add(home_team)
        db.flush()

    away_team = db.execute(
        select(Team).where(Team.league_id == league_id, Team.source_id == game.away_team_external_id)
    ).scalar_one_or_none()
    if away_team is None:
        away_team = Team(
            name=f"Team {game.away_team_external_id}",
            league_id=league_id,
            source_system=game.league,
            source_id=game.away_team_external_id,
        )
        db.add(away_team)
        db.flush()

    row = db.execute(
        select(Game).where(
            Game.league_id == league_id,
            Game.external_game_id == game.external_game_id,
        )
    ).scalar_one_or_none()
    if row is None:
        row = Game(
            league_id=league_id,
            external_game_id=game.external_game_id,
            source_id=game.external_game_id,
            game_date=game.game_date,
            season=f"{game.game_date.year}-{str((game.game_date.year + 1) % 100).zfill(2)}",
            home_team_id=home_team.id,
            away_team_id=away_team.id,
            home_team_external_id=game.home_team_external_id,
            away_team_external_id=game.away_team_external_id,
            status=game.status,
            source_updated_at=game.source_updated_at,
            raw_schedule_payload=json.dumps(game.raw_payload) if game.raw_payload else None,
        )
        db.add(row)
        db.flush()
        return row
    row.game_date = game.game_date
    row.status = game.status
    row.home_team_id = home_team.id
    row.away_team_id = away_team.id
    row.source_id = game.external_game_id
    row.home_team_external_id = game.home_team_external_id
    row.away_team_external_id = game.away_team_external_id
    row.source_updated_at = game.source_updated_at
    row.raw_schedule_payload = json.dumps(game.raw_payload) if game.raw_payload else row.raw_schedule_payload
    return row


def _checkpoint_discovery(db, *, league: str, start_date: date, end_date: date, discovered_games: int) -> None:
    checkpoint = db.execute(
        select(SyncCheckpoint).where(
            SyncCheckpoint.source == league.lower(),
            SyncCheckpoint.checkpoint_key == "schedule_last_discovery",
        )
    ).scalar_one_or_none()
    if checkpoint is None:
        checkpoint = SyncCheckpoint(source=league.lower(), checkpoint_key="schedule_last_discovery")
        db.add(checkpoint)
    checkpoint.checkpoint_value = datetime.utcnow().isoformat()
    checkpoint.checkpoint_metadata = json.dumps(
        {
            "from": start_date.isoformat(),
            "to": end_date.isoformat(),
            "discovered_games": discovered_games,
        }
    )
    checkpoint.updated_at = datetime.utcnow()


def needs_hydration(game: Game, *, now: Optional[datetime] = None, force: bool = False) -> bool:
    if force:
        return True
    if game.last_hydrated_at is None:
        return True
    if game.status != "final":
        return True
    if game.source_updated_at and game.last_hydrated_at and game.source_updated_at > game.last_hydrated_at:
        return True
    now_utc = now or datetime.utcnow()
    lookback = timedelta(hours=max(1, int(settings.stat_correction_lookback_hours)))
    return game.game_date >= (now_utc.date() - timedelta(days=max(1, int(lookback.total_seconds() // 86400))))


def discover_schedule(
    *,
    league: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
) -> ScheduleSyncResult:
    provider = _get_provider(league)
    today = date.today()
    start = start_date or (today - timedelta(days=max(0, int(settings.sync_lookback_days))))
    end = end_date or (today + timedelta(days=max(0, int(settings.sync_lookahead_days))))
    discovered = provider.discover_schedule(start_date=start, end_date=end)

    with SessionLocal() as db:
        league_row = _get_or_create_league(db, provider.league)
        for game in discovered:
            _upsert_discovered_game(db, league_id=league_row.id, game=game)
        _checkpoint_discovery(db, league=provider.league, start_date=start, end_date=end, discovered_games=len(discovered))
        db.commit()

    logger.info(
        "schedule_discovery league=%s from=%s to=%s discovered=%d",
        provider.league,
        start.isoformat(),
        end.isoformat(),
        len(discovered),
    )
    return ScheduleSyncResult(league=provider.league, discovered_games=len(discovered))


def hydrate_games(
    *,
    league: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    force: bool = False,
) -> ScheduleSyncResult:
    provider = _get_provider(league)
    if provider.league == "nfl" and not settings.enable_nfl_sync:
        return ScheduleSyncResult(league="nfl")

    today = date.today()
    start = start_date or (today - timedelta(days=max(0, int(settings.sync_lookback_days))))
    end = end_date or (today + timedelta(days=max(0, int(settings.sync_lookahead_days))))
    now = datetime.utcnow()

    with SessionLocal() as db:
        league_row = _get_or_create_league(db, provider.league)
        games = db.execute(
            select(Game).where(
                Game.league_id == league_row.id,
                Game.game_date >= start,
                Game.game_date <= end,
                Game.external_game_id.is_not(None),
            )
        ).scalars().all()
        to_hydrate = [game for game in games if needs_hydration(game, now=now, force=force)]

        hydrated = 0
        skipped = max(0, len(games) - len(to_hydrate))
        total_players = 0
        total_team_stats = 0
        total_player_stats = 0
        affected_player_ids: set[int] = set()
        affected_team_ids: set[int] = set()
        affected_game_ids: set[int] = set()

        for game in to_hydrate:
            try:
                detail = provider.fetch_game_detail(game.external_game_id or "")
            except Exception as exc:
                logger.warning("Skipping hydration for game %s (%s): %s", game.external_game_id, game.game_date, exc)
                continue
            load = load_nba_games_incremental(db, game_payloads=[detail.payload])
            game.last_hydrated_at = now
            game.last_synced_at = now
            game.status = detail.game.status
            if detail.game.source_updated_at is not None:
                game.source_updated_at = detail.game.source_updated_at
            hydrated += 1
            total_players += load.players_loaded
            total_team_stats += load.team_stats_loaded
            total_player_stats += load.stats_loaded
            affected_player_ids.update(load.affected_player_ids)
            affected_team_ids.update(load.affected_team_ids)
            affected_game_ids.update(load.affected_game_ids)

        sig: SignalGenerationResult
        if affected_player_ids or affected_team_ids:
            sig = generate_signals_for_players(db, list(affected_player_ids), team_ids=list(affected_team_ids))
        else:
            sig = SignalGenerationResult()
        db.commit()

    logger.info(
        "schedule_hydrate league=%s discovered=%d skipped=%d hydrated=%d players=%d team_stats=%d player_stats=%d signals_created=%d signals_updated=%d",
        provider.league,
        len(games),
        skipped,
        hydrated,
        total_players,
        total_team_stats,
        total_player_stats,
        sig.created_signals,
        sig.updated_signals,
    )
    return ScheduleSyncResult(
        league=provider.league,
        discovered_games=len(games),
        skipped_games=skipped,
        hydrated_games=hydrated,
        players_loaded=total_players,
        team_stats_loaded=total_team_stats,
        player_stats_loaded=total_player_stats,
        signals_created=sig.created_signals,
        signals_updated=sig.updated_signals,
    )


def sync_league(
    *,
    league: str,
    start_date: Optional[date] = None,
    end_date: Optional[date] = None,
    force: bool = False,
) -> ScheduleSyncResult:
    discovery = discover_schedule(league=league, start_date=start_date, end_date=end_date)
    hydration = hydrate_games(league=league, start_date=start_date, end_date=end_date, force=force)
    return ScheduleSyncResult(
        league=league.lower(),
        discovered_games=discovery.discovered_games,
        skipped_games=hydration.skipped_games,
        hydrated_games=hydration.hydrated_games,
        players_loaded=hydration.players_loaded,
        team_stats_loaded=hydration.team_stats_loaded,
        player_stats_loaded=hydration.player_stats_loaded,
        signals_created=hydration.signals_created,
        signals_updated=hydration.signals_updated,
    )
