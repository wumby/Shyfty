import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { EmptyState } from '../components/EmptyState';
import { LastGameShyftCard } from "../components/LastGameShyftCard";
import { LoadingState } from '../components/LoadingState';
import { SectionHeader } from '../components/SectionHeader';
import { ShyftCommentsDrawer } from "../components/ShyftCommentsDrawer";
import { ShyftDetailDrawer } from "../components/ShyftDetailDrawer";
import { api } from '../services/api';
import { useAuthStore } from '../store/useAuthStore';
import { useShyftStore } from "../store/useShyftStore";
import type { PlayerBoxScore, PlayerDetail, Shyft } from '../types';
import { formatGameContext, formatShyftLabel } from "../lib/shyftFormat";

type CommentThread = { shyftId: number; shyftIds: number[]; title: string; subtitle?: string };

function groupSignalsByGame(shyfts: Shyft[]): Shyft[][] {
  const grouped = new Map<string | number, Shyft[]>();
  for (const shyft of shyfts) {
    const key = shyft.game_id ?? shyft.event_date ?? 'unknown';
    const existing = grouped.get(key);
    if (existing) existing.push(shyft);
    else grouped.set(key, [shyft]);
  }
  return [...grouped.values()];
}

function formatBoxScoreValue(value: number, mode: 'number' | 'percent') {
  if (mode === 'percent') {
    const normalized = Math.abs(value) <= 1 ? value * 100 : value;
    return `${Number.isInteger(normalized) ? normalized.toFixed(0) : normalized.toFixed(1)}%`;
  }
  return Number.isInteger(value) ? value.toString() : value.toFixed(1);
}

function dashValue(value: number | null | undefined, mode: 'number' | 'percent') {
  if (typeof value !== 'number') return '—';
  return formatBoxScoreValue(value, mode);
}

function plusMinusValue(value: number | null | undefined) {
  if (typeof value !== 'number') return '—';
  return value > 0 ? `+${value}` : `${value}`;
}

function boxScoreTone(result?: string | null) {
  if (result === 'W') return { text: 'text-success', bg: 'bg-success/15', border: 'border-success/35' };
  if (result === 'L') return { text: 'text-danger', bg: 'bg-danger/15', border: 'border-danger/35' };
  return { text: 'text-muted', bg: 'bg-white/[0.05]', border: 'border-border' };
}

function PlayerBoxScores({ rows }: { rows: PlayerBoxScore[] }) {
  return (
    <section className="panel-surface px-4 py-4">
      <div className="flex items-center justify-between gap-3 px-1">
        <h2 className="text-base font-semibold text-ink">Recent Box Scores</h2>
        <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted">{rows.length}/5 games</span>
      </div>
      <div className="mt-3">
        {rows.length === 0 ? (
          <div className="rounded-[16px] border border-dashed border-borderStrong bg-white/[0.025] px-4 py-4 text-sm text-muted">
            No box scores are stored for this player yet.
          </div>
        ) : (
          <div className="overflow-hidden rounded-[16px] border border-border bg-white/[0.03]">
            {rows.map((row, index) => {
              const stats = [
                { label: 'PTS', value: dashValue(row.points, 'number') },
                { label: 'REB', value: dashValue(row.rebounds, 'number') },
                { label: 'AST', value: dashValue(row.assists, 'number') },
                { label: 'MIN', value: dashValue(row.minutes_played, 'number') },
                { label: 'FG%', value: dashValue(row.fg_pct, 'percent') },
                { label: '3P%', value: dashValue(row.fg3_pct, 'percent') },
                { label: '+/-', value: plusMinusValue(row.plus_minus) },
                { label: 'TO', value: dashValue(row.turnovers, 'number') },
                { label: 'STL', value: dashValue(row.steals, 'number') },
                { label: 'BLK', value: dashValue(row.blocks, 'number') },
              ];
              const tone = boxScoreTone(row.result);
              const score = row.team_score != null && row.opponent_score != null
                ? `${row.team_score}–${row.opponent_score}`
                : '—';

              return (
                <div key={row.game_id}>
                  <div className="px-3 py-2">
                    <div className="flex items-center justify-between gap-3">
                      <div className="min-w-0">
                        <div className="truncate text-sm font-semibold text-ink">
                          {row.home_away === 'Away' ? '@' : 'vs'} {row.opponent}
                        </div>
                        <div className="mt-0.5 truncate text-[11px] text-muted">{formatGameContextDate(row.game_date)}</div>
                      </div>
                      <div className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-semibold tabular-nums ${tone.bg} ${tone.border} ${tone.text}`}>
                        {(row.result ?? '—')} {score}
                      </div>
                    </div>

                    <div className="mt-2 grid grid-cols-5 gap-x-3 gap-y-1 md:grid-cols-10 md:gap-x-2">
                      {stats.map((stat) => (
                        <div key={`${row.game_id}-${stat.label}`} className="min-w-0 text-left">
                          <div className="text-[8px] font-semibold uppercase tracking-[0.1em] text-muted">{stat.label}</div>
                          <div className={`text-[14px] font-semibold tabular-nums ${stat.label === '+/-' && stat.value.startsWith('+') ? 'text-success' : stat.label === '+/-' && stat.value.startsWith('-') ? 'text-danger' : 'text-ink'}`}>
                            {stat.value}
                          </div>
                        </div>
                      ))}
                    </div>
                  </div>
                  {index < rows.length - 1 ? (
                    <div className="border-t border-white/10" />
                  ) : null}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}

function formatGameContextDate(value: string) {
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (dateOnly) {
    const [, year, month, day] = dateOnly;
    return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' })
      .format(new Date(Date.UTC(Number(year), Number(month) - 1, Number(day))));
  }
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value));
}

export function PlayerDetailPage() {
  const { id = '' } = useParams();
  const currentUser = useAuthStore((s) => s.currentUser);
  const openAuth = useAuthStore((s) => s.openAuth);
  const toggleFollowPlayer = useShyftStore((s) => s.toggleFollowPlayer);
  const profile = useShyftStore((s) => s.profile);
  const fetchProfile = useShyftStore((s) => s.fetchProfile);
  const shyftMetaById = useShyftStore((s) => s.shyftMetaById);
  const setShyftGroupCommentCount = useShyftStore((s) => s.setShyftGroupCommentCount);
  const mergeShyftMeta = useShyftStore((s) => s.mergeShyftMeta);

  const [player, setPlayer] = useState<PlayerDetail | null>(null);
  const [shyfts, setShyfts] = useState<Shyft[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detailShyftId, setDetailSignalId] = useState<number | null>(null);
  const [commentThread, setCommentThread] = useState<CommentThread | null>(null);

  useEffect(() => {
    if (!currentUser) return;
    void fetchProfile();
  }, [currentUser, fetchProfile]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        const [playerRes, shyftRes] = await Promise.all([
          api.getPlayer(id),
          api.getPlayerShyfts(id),
        ]);
        setPlayer(playerRes);
        setShyfts(shyftRes);
        shyftRes.forEach(mergeShyftMeta);
      } catch (loadError) {
        setError(loadError instanceof Error ? loadError.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [id, mergeShyftMeta]);

  useEffect(() => {
    setShyfts((prev) =>
      prev.map((shyft) => {
        const meta = shyftMetaById[shyft.id];
        if (!meta) return shyft;
        return {
          ...shyft,
          comment_count: meta.comment_count,
          reaction_summary: meta.reaction_summary,
          user_reaction: meta.user_reaction,
          reactions: meta.reactions,
          user_reactions: meta.user_reactions,
        };
      }),
    );
  }, [shyftMetaById]);

  const primaryShyft = shyfts[0] ?? null;
  const groupedShyfts = useMemo(() => groupSignalsByGame(shyfts), [shyfts]);
  const contextCards = useMemo(
    () => [
      { label: 'Team', value: player?.team_name ?? '—' },
      { label: 'League', value: player?.league_name ?? '—' },
      { label: 'Active Signals', value: String(shyfts.length) },
      { label: 'Latest Shyft', value: primaryShyft ? formatShyftLabel(primaryShyft.severity ?? primaryShyft.shyft_type) : 'None yet' },
    ],
    [player, primaryShyft, shyfts.length],
  );

  if (loading) return <LoadingState />;
  if (error || !player) return <EmptyState title="Player unavailable" copy={error ?? 'No player found.'} />;

  const isFollowed = profile?.follows.players.includes(player.id) ?? player.is_followed;

  async function handleFollow() {
    if (!currentUser) { openAuth('signin'); return; }
    await toggleFollowPlayer(player!.id, isFollowed);
  }

  return (
    <>
      <div className="space-y-4">
        <section className="panel-surface px-5 py-5 sm:px-6">
          <nav className="mb-4 flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
            <Link to="/players" className="transition hover:text-ink">Players</Link>
            <span className="text-white/20">/</span>
            <span className="text-ink">{player.name}</span>
          </nav>

          <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
            <div className="min-w-0">
              <div className="eyebrow">{player.league_name}</div>
              <h1 className="mt-2 text-3xl font-semibold text-ink sm:text-4xl">{player.name}</h1>
              <p className="mt-1.5 text-sm text-muted">{player.team_name} · {player.position}</p>
              {isFollowed ? (
                <div className="mt-3 inline-flex items-center gap-2 rounded-full border border-accent/35 bg-accentSoft px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#ffe2cb]">
                  <span className="h-2 w-2 rounded-full bg-accent shadow-[0_0_16px_rgba(249,115,22,0.7)]" />
                  Tracking
                </div>
              ) : null}
            </div>
            <button
              type="button"
              onClick={() => void handleFollow()}
              className={`shrink-0 rounded-full border px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] transition ${
                isFollowed
                  ? 'border-accent/40 bg-accentSoft text-accent hover:bg-accent/20'
                  : 'border-border bg-white/[0.04] text-muted hover:border-borderStrong hover:text-ink'
              }`}
            >
              {isFollowed ? '✓ Following' : '+ Follow'}
            </button>
          </div>

          <div className="mt-5 grid gap-3 sm:grid-cols-2 xl:grid-cols-4">
            {contextCards.map((card) => (
              <div key={card.label} className="rounded-[20px] border border-border bg-white/[0.03] px-4 py-4">
                <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">{card.label}</div>
                <div className="mt-2 text-xl font-semibold text-ink">{card.value}</div>
              </div>
            ))}
          </div>
        </section>

        <PlayerBoxScores rows={player.recent_box_scores} />

        {primaryShyft ? (
          <section className="panel-surface px-4 py-4">
            <SectionHeader
              title="Latest Context"
              description="What changed last game and why it got flagged."
            />
            <div className="mt-4 grid gap-4 lg:grid-cols-[minmax(0,1.4fr)_minmax(280px,0.9fr)]">
              <div className="rounded-[22px] border border-border bg-white/[0.03] px-4 py-4">
                <div className="eyebrow">Current Shyft</div>
                <div className="mt-2 text-2xl font-semibold text-ink">
                  {formatShyftLabel(primaryShyft.severity ?? primaryShyft.shyft_type)} on {primaryShyft.metric_label ?? primaryShyft.metric_name}
                </div>
                <p className="mt-2 text-sm leading-6 text-muted">{primaryShyft.explanation}</p>
                <div className="mt-3 text-sm text-[#ffd8bd]">{formatGameContext(primaryShyft)}</div>
              </div>
              <div className="rounded-[22px] border border-border bg-[#09172a]/80 px-4 py-4">
                <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">Why it surfaced</div>
                <div className="mt-3 flex items-end justify-between gap-3">
                  <div>
                    <div className="text-xs text-muted">Current</div>
                    <div className="text-2xl font-semibold text-ink">{primaryShyft.current_value}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted">Baseline</div>
                    <div className="text-xl font-semibold text-ink">{primaryShyft.baseline_value}</div>
                  </div>
                  <div>
                    <div className="text-xs text-muted">Z-score</div>
                    <div className="text-xl font-semibold text-[#ffd8bd]">{primaryShyft.z_score.toFixed(1)}</div>
                  </div>
                </div>
                <div className="mt-4 text-xs leading-5 text-muted">
                  Supporting context is intentionally tight here: enough to explain the shyft, not enough to turn this page into a long-range stats encyclopedia.
                </div>
              </div>
            </div>
          </section>
        ) : null}

        <section className="panel-surface px-4 py-4">
          <SectionHeader
            title="Recent Shyfts"
            description="Read the active shyfts first. If this list is empty, the player simply does not have a fresh shyft yet."
            aside={<div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">{shyfts.length} total</div>}
          />

          <div className="mt-4 space-y-4">
            {groupedShyfts.length === 0 ? (
              <div className="rounded-[20px] border border-dashed border-borderStrong bg-white/[0.03] px-4 py-5 text-sm text-muted">
                No recent shyfts are active for this player yet. This page will fill in once the next real-data sync produces shyft-worthy movement.
              </div>
            ) : (
              groupedShyfts.map((group) => (
                <LastGameShyftCard
                  key={`${group[0]?.player_id ?? group[0]?.team_id ?? 'unknown'}-${group[0]?.game_id ?? group[0]?.event_date ?? 'game'}`}
                  shyfts={group}
                  onOpenDetail={(shyftId) => setDetailSignalId(shyftId)}
                  onOpenComments={(shyftId, title, subtitle, shyftIds) =>
                    setCommentThread({ shyftId, title, subtitle, shyftIds: shyftIds?.length ? shyftIds : [shyftId] })
                  }
                />
              ))
            )}
          </div>
        </section>
      </div>

      {detailShyftId != null ? (
        <ShyftDetailDrawer shyftId={detailShyftId} onClose={() => setDetailSignalId(null)} />
      ) : null}
      {commentThread ? (
        <ShyftCommentsDrawer
          shyftId={commentThread.shyftId}
          title={commentThread.title}
          subtitle={commentThread.subtitle}
          onCountChange={(count) => {
            const ids = new Set(commentThread.shyftIds);
            setShyftGroupCommentCount(commentThread.shyftIds, count);
            setShyfts((prev) =>
              prev.map((shyft) =>
                ids.has(shyft.id) ? { ...shyft, comment_count: count } : shyft,
              ),
            );
          }}
          onClose={() => setCommentThread(null)}
        />
      ) : null}
    </>
  );
}
