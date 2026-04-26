"""NBA Stats API ingest source.

Implements IngestSource for the NBA Stats API (polled batch, source_type=API).
Wraps the existing fetch and incremental normalization services.

Each game's combined boxscore (traditional + advanced + usage) is treated as one IngestEvent,
matching the granularity a Kafka producer would use if this data were streamed.
"""
from __future__ import annotations

import json
import logging
from datetime import date, datetime, timedelta, timezone
from pathlib import Path
from typing import Any, Iterator, Optional

from sqlalchemy.orm import Session

from app.ingest.base import IngestEvent, IngestSource, LoadSummary, SourceType
from app.services.nba_ingest_service import (
    NBA_SOURCE_SYSTEM,
    FetchResult,
    fetch_recent_nba_data,
    raw_nba_root,
)

logger = logging.getLogger(__name__)


def _build_game_log_meta(snapshot_dir: Path) -> dict[str, dict]:
    """Extract per-game home/away/date metadata from a snapshot's leaguegamelog."""
    meta: dict[str, dict] = {}
    gl_path = snapshot_dir / "leaguegamelog.json"
    if not gl_path.exists():
        return meta
    try:
        gl_data = json.loads(gl_path.read_text(encoding="utf-8"))
        rs = next(
            (r for r in gl_data.get("resultSets", []) if r.get("name") == "LeagueGameLog"),
            None,
        )
        if rs is None:
            return meta
        hdrs = rs["headers"]
        for row in rs["rowSet"]:
            gl = dict(zip(hdrs, row))
            gid = str(gl.get("GAME_ID", ""))
            if not gid:
                continue
            matchup = gl.get("MATCHUP") or ""
            if gid not in meta:
                meta[gid] = {"game_date": gl.get("GAME_DATE"), "home_team_id": None, "away_team_id": None}
            if "vs." in matchup:
                meta[gid]["home_team_id"] = str(gl.get("TEAM_ID", ""))
            elif "@" in matchup:
                meta[gid]["away_team_id"] = str(gl.get("TEAM_ID", ""))
    except Exception:
        logger.debug("Could not parse leaguegamelog from %s", snapshot_dir)
    return meta


def _has_real_player_stats(trad_path: Path) -> bool:
    """Return True if the traditional boxscore file has at least one PlayerStats row."""
    try:
        data = json.loads(trad_path.read_text(encoding="utf-8"))
        for rs in data.get("resultSets", []):
            if rs.get("name") == "PlayerStats":
                return len(rs.get("rowSet", [])) > 0
    except Exception:
        pass
    return False


def _iter_snapshot_events(
    snapshot_dir: Path,
    game_log_meta: dict[str, dict],
    seen_game_ids: set[str],
) -> Iterator[IngestEvent]:
    """Yield IngestEvents for games in snapshot_dir that haven't been seen yet."""
    manifest_path = snapshot_dir / "manifest.json"
    if not manifest_path.exists():
        # Build synthetic manifest from whatever game files exist.
        game_files = sorted((snapshot_dir / "games").glob("*_traditional.json")) if (snapshot_dir / "games").exists() else []
        game_ids = [f.stem.replace("_traditional", "") for f in game_files]
    else:
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        game_ids = manifest.get("game_ids", [])

    for game_id in game_ids:
        if game_id in seen_game_ids:
            continue
        trad_path = snapshot_dir / "games" / f"{game_id}_traditional.json"
        if not trad_path.exists() or not _has_real_player_stats(trad_path):
            continue
        adv_path = snapshot_dir / "games" / f"{game_id}_advanced.json"
        usage_path = snapshot_dir / "games" / f"{game_id}_usage.json"

        seen_game_ids.add(game_id)
        yield IngestEvent(
            source=NBA_SOURCE_SYSTEM,
            source_type=SourceType.API,
            external_id=str(game_id),
            event_timestamp=None,
            ingested_at=datetime.now(timezone.utc).replace(tzinfo=None),
            raw_payload={
                "source_system": NBA_SOURCE_SYSTEM,
                "game_id": game_id,
                "snapshot_dir": str(snapshot_dir),
                "traditional": json.loads(trad_path.read_text(encoding="utf-8")),
                "advanced": json.loads(adv_path.read_text(encoding="utf-8")) if adv_path.exists() else {},
                "usage": json.loads(usage_path.read_text(encoding="utf-8")) if usage_path.exists() else {},
                "game_log_meta": game_log_meta.get(str(game_id)),
            },
        )


def _find_salvageable_snapshots(exclude_dir: Path) -> list[Path]:
    """Return snapshot dirs (excluding exclude_dir) that have at least one game file with real data."""
    root = raw_nba_root()
    candidates: list[Path] = []
    for d in sorted(root.iterdir(), reverse=True):
        if not d.is_dir() or d.name == "LATEST" or d == exclude_dir:
            continue
        games_dir = d / "games"
        if not games_dir.exists():
            continue
        if any(_has_real_player_stats(f) for f in games_dir.glob("*_traditional.json")):
            candidates.append(d)
    return candidates


_SNAPSHOT_CACHE_HOURS = 4.0
_OFFSEASON_FALLBACK_DAYS_BACK = 365


def _reuse_or_fetch(
    *,
    season: Optional[str],
    days_back: int,
    max_games: int,
    season_type: str = "Regular Season",
    force_fetch: bool = False,
) -> FetchResult:
    """Return a recent on-disk snapshot if it's fresh enough, otherwise call the NBA API.

    Skips the 3-5 minute sleep-gated API round-trip when an equivalent snapshot was
    already written within _SNAPSHOT_CACHE_HOURS. Because reset-dev.sh keeps raw
    snapshots, this short-circuits the fetch on every subsequent reset-dev cycle
    within the same day.
    """
    root = raw_nba_root()
    cutoff = datetime.now(timezone.utc) - timedelta(hours=_SNAPSHOT_CACHE_HOURS)

    if not force_fetch:
        for d in sorted(root.iterdir(), reverse=True):
            if not d.is_dir() or d.name == "LATEST":
                continue
            try:
                snap_time = datetime.strptime(d.name[:16], "%Y%m%dT%H%M%SZ").replace(tzinfo=timezone.utc)
            except ValueError:
                continue
            if snap_time < cutoff:
                break
            manifest_path = d / "manifest.json"
            if not manifest_path.exists():
                continue
            try:
                manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
                # Treat missing season_type as Regular Season (older snapshots).
                snap_type = manifest.get("season_type") or "Regular Season"
                if snap_type != season_type:
                    continue
                logger.info(
                    "NBA: reusing %s snapshot %s (< %.0fh old, skipping API call)",
                    season_type, d.name, _SNAPSHOT_CACHE_HOURS,
                )
                return FetchResult(
                    output_dir=d,
                    manifest_path=manifest_path,
                    game_count=len(manifest.get("game_ids", [])),
                    team_count=len(manifest.get("team_ids", [])),
                    roster_count=0,
                    skipped_games=manifest.get("skipped_games", 0),
                )
            except Exception:
                continue

    return fetch_recent_nba_data(
        season=season,
        season_type=season_type,
        days_back=days_back,
        max_games=max_games,
    )


class NBASAPISource(IngestSource):
    """NBA Stats API batch ingest source.

    Fetches game data via the NBA Stats API, writes raw JSON snapshots to disk,
    then loads each game incrementally into the DB with idempotency checks.

    Future Kafka analog: a KafkaNBABoxscoreSource would implement the same interface
    but consume from a Kafka topic instead of polling the REST API. The load_events()
    implementation would be identical.
    """

    @property
    def source_name(self) -> str:
        return NBA_SOURCE_SYSTEM

    @property
    def source_type(self) -> SourceType:
        return SourceType.API

    def fetch_events(
        self,
        *,
        season: Optional[str] = None,
        days_back: int = 21,
        max_games: int = 50,
        **kwargs,
    ) -> Iterator[IngestEvent]:
        """Fetch recent NBA games and yield one IngestEvent per game.

        Strategy:
        1. Fetch Regular Season. If the API returns empty boxscores (rate-limited silent
           failure), rescue valid games from recently-downloaded on-disk snapshots.
        2. During the playoff window (April–June), also fetch Playoffs so signals
           reflect current post-season games alongside the regular-season baseline.
        """
        seen_game_ids: set[str] = set()

        # --- Regular Season ---
        reg_result = _reuse_or_fetch(season=season, days_back=days_back, max_games=max_games, season_type="Regular Season")
        reg_meta = _build_game_log_meta(reg_result.output_dir)

        reg_events = list(_iter_snapshot_events(reg_result.output_dir, reg_meta, seen_game_ids))
        if not reg_events and days_back < _OFFSEASON_FALLBACK_DAYS_BACK:
            logger.info(
                "NBA: no Regular Season games in the %d-day window; widening to each player's latest games",
                days_back,
            )
            reg_result = _reuse_or_fetch(
                season=season,
                days_back=_OFFSEASON_FALLBACK_DAYS_BACK,
                max_games=max_games,
                season_type="Regular Season",
                force_fetch=True,
            )
            reg_meta = _build_game_log_meta(reg_result.output_dir)
            reg_events = list(_iter_snapshot_events(reg_result.output_dir, reg_meta, seen_game_ids))

        if reg_events:
            logger.info("NBA: loaded %d Regular Season games with real stats", len(reg_events))
            yield from reg_events
        else:
            # API returned empty boxscores for all Regular Season games (likely rate-limited or
            # season ended). Salvage valid game files from recent on-disk snapshots.
            salvage_dirs = _find_salvageable_snapshots(exclude_dir=reg_result.output_dir)
            if salvage_dirs:
                logger.info(
                    "NBA: Regular Season snapshot has no real stats; salvaging from %d on-disk snapshots",
                    len(salvage_dirs),
                )
                for snap_dir in salvage_dirs:
                    snap_meta = _build_game_log_meta(snap_dir)
                    yield from _iter_snapshot_events(snap_dir, snap_meta, seen_game_ids)
            else:
                logger.info("NBA: no Regular Season games found from API or disk")

        # --- Playoffs (April–June) ---
        today = date.today()
        if 4 <= today.month <= 6:
            playoffs_result = _reuse_or_fetch(
                season=season,
                days_back=days_back,
                max_games=max_games,
                season_type="Playoffs",
            )
            playoffs_meta = _build_game_log_meta(playoffs_result.output_dir)
            playoff_events = list(_iter_snapshot_events(playoffs_result.output_dir, playoffs_meta, seen_game_ids))
            if playoff_events:
                logger.info("NBA: loaded %d Playoff games", len(playoff_events))
                yield from playoff_events
            else:
                logger.info("NBA: no Playoff games found")

    def load_events(self, db: Session, events: list[IngestEvent]) -> LoadSummary:
        """Normalize and incrementally load a batch of NBA game events.

        Idempotent: skips player_game_stats rows that already exist for the same
        (source_system, source_game_id, source_player_id). Does not wipe existing data.
        """
        from app.services.nba_normalization_service import load_nba_games_incremental

        game_payloads = [e.raw_payload for e in events]
        result = load_nba_games_incremental(db, game_payloads=game_payloads)
        return LoadSummary(
            teams_loaded=result.teams_loaded,
            players_loaded=result.players_loaded,
            games_loaded=result.games_loaded,
            stats_loaded=result.stats_loaded,
            skipped_stat_rows=result.skipped_stat_rows,
            affected_player_ids=result.affected_player_ids,
            affected_team_ids=result.affected_team_ids,
            affected_game_ids=result.affected_game_ids,
        )
