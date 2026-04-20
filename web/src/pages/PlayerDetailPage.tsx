import { useEffect, useState } from 'react';
import { Link, useLocation, useParams } from 'react-router-dom';

import { EmptyState } from '../components/EmptyState';
import { LoadingState } from '../components/LoadingState';
import { PlayerHeader } from '../components/PlayerHeader';
import { SignalCard } from '../components/SignalCard';
import { SignalDetailDrawer } from '../components/SignalDetailDrawer';
import { TrendChart } from '../components/TrendChart';
import { api } from '../services/api';
import { useAuthStore } from '../store/useAuthStore';
import { useSignalStore } from '../store/useSignalStore';
import type { GameLogRow, MetricSeriesPoint, PlayerDetail, SeasonAveragesRow, Signal } from '../types';

// ── Season comparison table ───────────────────────────────────────────────────

function fmt(val: number | null, decimals = 1): string {
  return val == null ? '—' : val.toFixed(decimals);
}

function Delta({ current, prior }: { current: number | null; prior: number | null }) {
  if (current == null || prior == null) return null;
  const diff = current - prior;
  if (Math.abs(diff) < 0.05) return <span className="text-muted text-[11px]">—</span>;
  const up = diff > 0;
  return (
    <span className={`text-[11px] font-medium ${up ? 'text-green-400' : 'text-red-400'}`}>
      {up ? '↑' : '↓'} {Math.abs(diff).toFixed(1)}
    </span>
  );
}

function SeasonComparisonTable({ rows, league }: { rows: SeasonAveragesRow[]; league: string }) {
  const isNBA = league === 'NBA';
  const current = rows[0] ?? null;
  const prior = rows[1] ?? null;

  if (!current) return null;

  const nbaStats = [
    { label: 'PPG', cur: current.points, pri: prior?.points },
    { label: 'RPG', cur: current.rebounds, pri: prior?.rebounds },
    { label: 'APG', cur: current.assists, pri: prior?.assists },
    { label: 'GP', cur: current.games_played, pri: prior?.games_played, noDecimal: true },
  ];
  const nflStats = [
    { label: 'Pass Yds', cur: current.passing_yards, pri: prior?.passing_yards, decimals: 0 },
    { label: 'Rush Yds', cur: current.rushing_yards, pri: prior?.rushing_yards, decimals: 0 },
    { label: 'Rec Yds', cur: current.receiving_yards, pri: prior?.receiving_yards, decimals: 0 },
    { label: 'TD/G', cur: current.touchdowns, pri: prior?.touchdowns },
    { label: 'GP', cur: current.games_played, pri: prior?.games_played, noDecimal: true },
  ];
  const stats = isNBA ? nbaStats : nflStats;

  return (
    <section className="panel-surface px-5 py-4">
      <div className="eyebrow mb-3">Season Averages</div>
      <div className="overflow-x-auto">
        <table className="w-full text-sm">
          <thead>
            <tr className="border-b border-border text-[10px] uppercase tracking-[0.14em] text-muted">
              <th className="pb-2 pr-4 text-left font-semibold">Season</th>
              {stats.map((s) => (
                <th key={s.label} className="pb-2 pr-3 text-right font-semibold">{s.label}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {rows.map((row, idx) => {
              const prevRow = rows[idx + 1] ?? null;
              type Cell = { val: number | null; pri: number | null | undefined; noDecimal?: boolean; decimals?: number };
              const cells: Cell[] = isNBA
                ? [
                    { val: row.points, pri: prevRow?.points },
                    { val: row.rebounds, pri: prevRow?.rebounds },
                    { val: row.assists, pri: prevRow?.assists },
                    { val: row.games_played, pri: prevRow?.games_played, noDecimal: true },
                  ]
                : [
                    { val: row.passing_yards, pri: prevRow?.passing_yards, decimals: 0 },
                    { val: row.rushing_yards, pri: prevRow?.rushing_yards, decimals: 0 },
                    { val: row.receiving_yards, pri: prevRow?.receiving_yards, decimals: 0 },
                    { val: row.touchdowns, pri: prevRow?.touchdowns },
                    { val: row.games_played, pri: prevRow?.games_played, noDecimal: true },
                  ];
              return (
                <tr key={row.season} className="border-b border-border/40 last:border-0">
                  <td className="py-2.5 pr-4 font-medium text-ink">{row.season}</td>
                  {cells.map((cell, ci) => (
                    <td key={ci} className="py-2.5 pr-3 text-right">
                      <div className="text-ink font-semibold">
                        {cell.noDecimal ? String(cell.val ?? '—') : fmt(cell.val, cell.decimals ?? 1)}
                      </div>
                      {idx === 0 && (
                        <Delta current={cell.val} prior={cell.pri ?? null} />
                      )}
                    </td>
                  ))}
                </tr>
              );
            })}
          </tbody>
        </table>
      </div>
    </section>
  );
}

// ── Game log table ───────────────────────────────────────────────────────────

function GameLogTable({
  rows,
  league,
  seasons,
  selectedSeason,
  onSeasonChange,
}: {
  rows: GameLogRow[];
  league: string;
  seasons: string[];
  selectedSeason: string | null;
  onSeasonChange: (s: string | null) => void;
}) {
  const isNBA = league === 'NBA';

  return (
    <section className="panel-surface px-4 py-4">
      <div className="mb-3 flex items-center justify-between">
        <div className="eyebrow">Game Log</div>
        {seasons.length > 1 && (
          <select
            value={selectedSeason ?? ''}
            onChange={(e) => onSeasonChange(e.target.value || null)}
            className="rounded-md border border-border bg-transparent px-2 py-1 text-[11px] text-muted focus:outline-none"
          >
            <option value="">All seasons</option>
            {seasons.map((s) => (
              <option key={s} value={s}>{s}</option>
            ))}
          </select>
        )}
      </div>
      <div className="overflow-x-auto">
        <table className="w-full min-w-[480px] text-sm">
          <thead>
            <tr className="border-b border-border text-[10px] uppercase tracking-[0.14em] text-muted">
              <th className="pb-2 pr-4 text-left font-semibold">Date</th>
              <th className="pb-2 pr-4 text-left font-semibold">Opponent</th>
              {isNBA ? (
                <>
                  <th className="pb-2 pr-4 text-right font-semibold">PTS</th>
                  <th className="pb-2 pr-4 text-right font-semibold">REB</th>
                  <th className="pb-2 pr-4 text-right font-semibold">AST</th>
                </>
              ) : (
                <>
                  <th className="pb-2 pr-4 text-right font-semibold">Pass</th>
                  <th className="pb-2 pr-4 text-right font-semibold">Rush</th>
                  <th className="pb-2 pr-4 text-right font-semibold">Rec</th>
                  <th className="pb-2 pr-4 text-right font-semibold">TD</th>
                </>
              )}
            </tr>
          </thead>
          <tbody>
            {rows.map((row) => (
              <tr key={row.game_id} className="border-b border-border/40 last:border-0">
                <td className="py-2.5 pr-4 text-muted">{row.game_date}</td>
                <td className="py-2.5 pr-4 text-ink">
                  <span className="text-muted">{row.home_away === 'Away' ? '@ ' : 'vs '}</span>
                  {row.opponent}
                </td>
                {isNBA ? (
                  <>
                    <td className="py-2.5 pr-4 text-right font-semibold text-ink">{row.points ?? '—'}</td>
                    <td className="py-2.5 pr-4 text-right text-ink">{row.rebounds ?? '—'}</td>
                    <td className="py-2.5 pr-4 text-right text-ink">{row.assists ?? '—'}</td>
                  </>
                ) : (
                  <>
                    <td className="py-2.5 pr-4 text-right font-semibold text-ink">{row.passing_yards ?? '—'}</td>
                    <td className="py-2.5 pr-4 text-right text-ink">{row.rushing_yards ?? '—'}</td>
                    <td className="py-2.5 pr-4 text-right text-ink">{row.receiving_yards ?? '—'}</td>
                    <td className="py-2.5 pr-4 text-right text-ink">{row.touchdowns ?? '—'}</td>
                  </>
                )}
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && (
          <p className="py-6 text-center text-sm text-muted">No game log data yet.</p>
        )}
      </div>
    </section>
  );
}

// ── Page ─────────────────────────────────────────────────────────────────────

export function PlayerDetailPage() {
  const { id = '' } = useParams();
  const location = useLocation();
  const [player, setPlayer] = useState<PlayerDetail | null>(null);
  const [signals, setSignals] = useState<Signal[]>([]);
  const [allGamelog, setAllGamelog] = useState<GameLogRow[]>([]);
  const [gamelog, setGamelog] = useState<GameLogRow[]>([]);
  const [seasonAverages, setSeasonAverages] = useState<SeasonAveragesRow[]>([]);
  const [metrics, setMetrics] = useState<MetricSeriesPoint[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [showAllSignals, setShowAllSignals] = useState(false);
  const [detailSignalId, setDetailSignalId] = useState<number | null>(null);
  const [selectedSeason, setSelectedSeason] = useState<string | null>(null);
  const currentUser = useAuthStore((state) => state.currentUser);
  const fetchProfile = useSignalStore((state) => state.fetchProfile);

  useEffect(() => {
    if (!currentUser) return;
    void fetchProfile();
  }, [currentUser, fetchProfile]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [playerRes, signalRes, gamelogRes, metricRes, seasonAvgRes] = await Promise.all([
          api.getPlayer(id),
          api.getPlayerSignals(id),
          api.getPlayerGamelog(id),
          api.getPlayerMetrics(id),
          api.getPlayerSeasonAverages(id),
        ]);
        setPlayer(playerRes);
        setSignals(signalRes);
        setAllGamelog(gamelogRes);
        setGamelog(gamelogRes);
        setMetrics(metricRes);
        setSeasonAverages(seasonAvgRes);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }
    void load();
  }, [id]);

  useEffect(() => {
    if (selectedSeason) {
      setGamelog(allGamelog.filter((r) => r.season === selectedSeason));
    } else {
      setGamelog(allGamelog);
    }
  }, [selectedSeason, allGamelog]);

  if (loading) return <LoadingState />;
  if (error || !player) return <EmptyState title="Player unavailable" copy={error ?? 'No player found.'} />;

  const seasons = [...new Set(allGamelog.map((r) => r.season).filter((s): s is string => s != null))].sort().reverse();
  const visibleSignals = showAllSignals ? signals : signals.slice(0, 5);

  return (
    <>
      <div className="space-y-5">
        <div className="px-1">
          <Link
            to={(location.state as { returnTo?: string } | null)?.returnTo ?? '/'}
            className="inline-flex items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted transition hover:text-[#ffd8bd]"
          >
            Back to feed
          </Link>
        </div>

        <PlayerHeader player={player} />

        {seasonAverages.length > 0 && (
          <SeasonComparisonTable rows={seasonAverages} league={player.league_name} />
        )}

        {/* Latest signals */}
        <section>
          <div className="mb-2 flex items-center justify-between px-1">
            <div className="eyebrow">
              {signals.length > 0 ? `Latest Signals · ${signals.length} total` : 'Latest Signals'}
            </div>
          </div>
          {signals.length === 0 ? (
            <div className="panel-surface px-4 py-6 text-center text-sm text-muted">No signals yet.</div>
          ) : (
            <div className="space-y-2">
              {visibleSignals.map((signal) => (
                <SignalCard
                  key={signal.id}
                  signal={signal}
                  onOpenDetail={(sid) => setDetailSignalId(sid)}
                />
              ))}
              {signals.length > 5 && (
                <button
                  type="button"
                  onClick={() => setShowAllSignals((v) => !v)}
                  className="w-full rounded-[22px] border border-border bg-white/[0.02] py-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted transition hover:text-ink"
                >
                  {showAllSignals ? 'Show less' : `Show all ${signals.length} signals`}
                </button>
              )}
            </div>
          )}
        </section>

        <GameLogTable
          rows={gamelog}
          league={player.league_name}
          seasons={seasons}
          selectedSeason={selectedSeason}
          onSeasonChange={setSelectedSeason}
        />

        {metrics.length > 0 && (
          <TrendChart data={metrics} signals={signals} />
        )}
      </div>

      {detailSignalId != null && (
        <SignalDetailDrawer signalId={detailSignalId} onClose={() => setDetailSignalId(null)} />
      )}
    </>
  );
}
