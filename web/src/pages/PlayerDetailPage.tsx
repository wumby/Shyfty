import { useEffect, useState } from 'react';
import { useParams } from 'react-router-dom';

import { EmptyState } from '../components/EmptyState';
import { LoadingState } from '../components/LoadingState';
import { PageIntro } from '../components/PageIntro';
import { PlayerHeader } from '../components/PlayerHeader';
import { SectionHeader } from '../components/SectionHeader';
import { SignalCard } from '../components/SignalCard';
import { SignalDetailDrawer } from '../components/SignalDetailDrawer';
import { TrendChart } from '../components/TrendChart';
import { api } from '../services/api';
import type { GameLogRow, MetricSeriesPoint, PlayerDetail, SeasonAveragesRow, Signal } from '../types';

function formatValue(value: number | null, decimals = 1) {
  return value == null ? '—' : value.toFixed(decimals);
}

function KeyStatsRow({ player, rows }: { player: PlayerDetail; rows: SeasonAveragesRow[] }) {
  const current = rows[0];

  if (!current) {
    return (
      <section className="panel-surface px-4 py-4">
        <SectionHeader
          title="Key Stats"
          description="Season-level averages will appear here once enough data has been ingested."
        />
      </section>
    );
  }

  const stats =
    player.league_name === 'NBA'
      ? [
          { label: 'PPG', value: formatValue(current.points) },
          { label: 'RPG', value: formatValue(current.rebounds) },
          { label: 'APG', value: formatValue(current.assists) },
        ]
      : [
          { label: 'Pass Yds', value: formatValue(current.passing_yards, 0) },
          { label: 'Rush Yds', value: formatValue(current.rushing_yards, 0) },
          { label: 'Rec Yds', value: formatValue(current.receiving_yards, 0) },
        ];

  return (
    <section className="panel-surface px-4 py-4">
      <SectionHeader
        title="Key Stats"
        description="Use these quick numbers to orient yourself before reading recent signals or the game log."
      />
      <div className="mt-4 grid gap-3 sm:grid-cols-3">
        {stats.map((stat) => (
          <div key={stat.label} className="rounded-[20px] bg-white/[0.03] px-4 py-4">
            <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">{stat.label}</div>
            <div className="mt-2 text-2xl font-semibold text-ink">{stat.value}</div>
          </div>
        ))}
      </div>
    </section>
  );
}

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
  onSeasonChange: (value: string | null) => void;
}) {
  const isNBA = league === 'NBA';

  return (
    <section className="panel-surface px-4 py-4">
      <SectionHeader
        title="Game Log"
        description="Review the recent game-by-game performance behind the profile and signals."
        aside={
          seasons.length > 1 ? (
            <select
              value={selectedSeason ?? ''}
              onChange={(e) => onSeasonChange(e.target.value || null)}
              className="field-shell px-3 py-2 text-sm"
            >
              <option value="">All seasons</option>
              {seasons.map((season) => (
                <option key={season} value={season}>{season}</option>
              ))}
            </select>
          ) : null
        }
      />

      <div className="mt-4 overflow-x-auto">
        <table className="w-full min-w-[540px] text-sm">
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
        {rows.length === 0 ? (
          <p className="py-6 text-center text-sm text-muted">Game log data has not been loaded for this player yet.</p>
        ) : null}
      </div>
    </section>
  );
}

export function PlayerDetailPage() {
  const { id = '' } = useParams();
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
    setGamelog(selectedSeason ? allGamelog.filter((row) => row.season === selectedSeason) : allGamelog);
  }, [selectedSeason, allGamelog]);

  if (loading) return <LoadingState />;
  if (error || !player) return <EmptyState title="Player unavailable" copy={error ?? 'No player found.'} />;

  const seasons = [...new Set(allGamelog.map((row) => row.season).filter((season): season is string => season != null))].sort().reverse();
  const visibleSignals = showAllSignals ? signals : signals.slice(0, 5);

  return (
    <>
      <div className="space-y-4">
        <PageIntro
          eyebrow="Player Profile"
          title={player.name}
          description={`Review ${player.team_name} context, recent signals, and game-level performance in one place.`}
          breadcrumbs={[
            { label: 'Teams', to: '/teams' },
            { label: player.team_name },
            { label: player.name },
          ]}
        />

        <PlayerHeader player={player} />

        <KeyStatsRow player={player} rows={seasonAverages} />

        <section className="panel-surface px-4 py-4">
          <SectionHeader
            title="Recent Signals"
            description="Start here to see why this player is surfacing now, then move into the game log for underlying detail."
            aside={<div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">{signals.length} total</div>}
          />

          <div className="mt-4">
            {signals.length === 0 ? (
              <div className="rounded-[20px] bg-white/[0.03] px-4 py-5 text-sm text-muted">
                No recent signals are active for this player. Use the game log below to review performance until new signals appear.
              </div>
            ) : (
              <div className="space-y-2">
                {visibleSignals.map((signal) => (
                  <SignalCard key={signal.id} signal={signal} onOpenDetail={(signalId) => setDetailSignalId(signalId)} />
                ))}
                {signals.length > 5 ? (
                  <button
                    type="button"
                    onClick={() => setShowAllSignals((value) => !value)}
                    className="w-full rounded-[22px] border border-border bg-white/[0.02] py-3 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted transition hover:text-ink"
                  >
                    {showAllSignals ? 'Show less' : `Show all ${signals.length} signals`}
                  </button>
                ) : null}
              </div>
            )}
          </div>
        </section>

        <GameLogTable
          rows={gamelog}
          league={player.league_name}
          seasons={seasons}
          selectedSeason={selectedSeason}
          onSeasonChange={setSelectedSeason}
        />

        {metrics.length > 0 ? (
          <section className="panel-surface px-4 py-4">
            <SectionHeader
              title="Trend Context"
              description="Use the trend view for longer-term context after reviewing the current profile and game log."
            />
            <div className="mt-4">
              <TrendChart data={metrics} signals={signals} />
            </div>
          </section>
        ) : null}
      </div>

      {detailSignalId != null ? (
        <SignalDetailDrawer signalId={detailSignalId} onClose={() => setDetailSignalId(null)} />
      ) : null}
    </>
  );
}
