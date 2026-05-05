import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { EmptyState } from '../components/EmptyState';
import { LastGameShyftCard } from "../components/LastGameShyftCard";
import { LoadingState } from '../components/LoadingState';
import { SectionHeader } from '../components/SectionHeader';
import { ShyftCommentsDrawer } from "../components/ShyftCommentsDrawer";
import { ShyftDetailDrawer } from "../components/ShyftDetailDrawer";
import { useAuthStore } from '../store/useAuthStore';
import { useShyftStore } from "../store/useShyftStore";
import { api } from '../services/api';
import type { Shyft, TeamBoxScore, TeamDetail } from '../types';

type CommentThread = { shyftId: number; shyftIds: number[]; title: string; subtitle?: string };

function groupSignalsByPlayerGame(shyfts: Shyft[]): Shyft[][] {
  const grouped = new Map<string, Shyft[]>();
  for (const shyft of shyfts) {
    const key = `${shyft.player_id ?? shyft.team_id}:${shyft.game_id ?? shyft.event_date ?? 'unknown'}`;
    const existing = grouped.get(key);
    if (existing) existing.push(shyft);
    else grouped.set(key, [shyft]);
  }
  return [...grouped.values()];
}

function formatTeamBoxScoreValue(value: number, mode: 'number' | 'percent') {
  if (mode === 'percent') {
    const normalized = Math.abs(value) <= 1 ? value * 100 : value;
    return `${Number.isInteger(normalized) ? normalized.toFixed(0) : normalized.toFixed(1)}%`;
  }
  return Number.isInteger(value) ? value.toString() : value.toFixed(1);
}

function formatBoxScoreDate(value: string) {
  const dateOnly = /^(\d{4})-(\d{2})-(\d{2})$/.exec(value);
  if (dateOnly) {
    const [, year, month, day] = dateOnly;
    return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric', timeZone: 'UTC' })
      .format(new Date(Date.UTC(Number(year), Number(month) - 1, Number(day))));
  }
  return new Intl.DateTimeFormat(undefined, { month: 'short', day: 'numeric', year: 'numeric' }).format(new Date(value));
}

function teamBoxScoreTone(result?: string | null) {
  if (result === 'W') return { text: 'text-success', bg: 'bg-success/15', border: 'border-success/35' };
  if (result === 'L') return { text: 'text-danger', bg: 'bg-danger/15', border: 'border-danger/35' };
  return { text: 'text-muted', bg: 'bg-white/[0.05]', border: 'border-border' };
}

function TeamBoxScores({ rows }: { rows: TeamBoxScore[] }) {
  return (
    <section className="panel-surface px-4 py-4">
      <div className="flex items-center justify-between gap-3 px-1">
        <h2 className="text-base font-semibold text-ink">Recent Box Scores</h2>
        <span className="text-[10px] font-semibold uppercase tracking-[0.14em] text-muted">{rows.length}/5 games</span>
      </div>
      <div className="mt-3">
        {rows.length === 0 ? (
          <div className="rounded-[16px] border border-dashed border-borderStrong bg-white/[0.025] px-4 py-4 text-sm text-muted">
            No team box scores are stored yet.
          </div>
        ) : (
          <div className="overflow-hidden rounded-[16px] border border-border bg-white/[0.03]">
            {rows.map((row, index) => {
              const stats = [
                { label: 'PTS', value: typeof row.points === 'number' ? formatTeamBoxScoreValue(row.points, 'number') : '—' },
                { label: 'REB', value: typeof row.rebounds === 'number' ? formatTeamBoxScoreValue(row.rebounds, 'number') : '—' },
                { label: 'AST', value: typeof row.assists === 'number' ? formatTeamBoxScoreValue(row.assists, 'number') : '—' },
                { label: 'TO', value: typeof row.turnovers === 'number' ? formatTeamBoxScoreValue(row.turnovers, 'number') : '—' },
                { label: 'FG%', value: typeof row.fg_pct === 'number' ? formatTeamBoxScoreValue(row.fg_pct, 'percent') : '—' },
                { label: '3P%', value: typeof row.fg3_pct === 'number' ? formatTeamBoxScoreValue(row.fg3_pct, 'percent') : '—' },
              ];
              const tone = teamBoxScoreTone(row.result);
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
                        <div className="mt-0.5 truncate text-[11px] text-muted">{formatBoxScoreDate(row.game_date)}</div>
                      </div>
                      <div className={`shrink-0 rounded-full border px-2 py-0.5 text-[11px] font-semibold tabular-nums ${tone.bg} ${tone.border} ${tone.text}`}>
                        {(row.result ?? '—')} {score}
                      </div>
                    </div>

                    <div className="mt-2 grid grid-cols-3 gap-x-3 gap-y-1 md:grid-cols-6 md:gap-x-2">
                      {stats.map((stat) => (
                        <div key={`${row.game_id}-${stat.label}`} className="min-w-0 text-left">
                          <div className="text-[8px] font-semibold uppercase tracking-[0.1em] text-muted">{stat.label}</div>
                          <div className="text-[14px] font-semibold tabular-nums text-ink">{stat.value}</div>
                        </div>
                      ))}
                    </div>
                  </div>
                  {index < rows.length - 1 ? <div className="border-t border-white/10" /> : null}
                </div>
              );
            })}
          </div>
        )}
      </div>
    </section>
  );
}

export function TeamDetailPage() {
  const { id = '' } = useParams();
  const currentUser = useAuthStore((state) => state.currentUser);
  const openAuth = useAuthStore((state) => state.openAuth);
  const fetchProfile = useShyftStore((state) => state.fetchProfile);
  const toggleFollowTeam = useShyftStore((state) => state.toggleFollowTeam);
  const setShyftGroupCommentCount = useShyftStore((state) => state.setShyftGroupCommentCount);
  const mergeShyftMeta = useShyftStore((state) => state.mergeShyftMeta);
  const profile = useShyftStore((state) => state.profile);
  const shyftMetaById = useShyftStore((state) => state.shyftMetaById);
  const [team, setTeam] = useState<TeamDetail | null>(null);
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
        const loadedTeam = await api.getTeam(id);
        setTeam(loadedTeam);
        loadedTeam.recent_shyfts.forEach(mergeShyftMeta);
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [id, mergeShyftMeta]);

  useEffect(() => {
    setTeam((prev) => {
      if (!prev) return prev;
      const nextSignals = prev.recent_shyfts.map((shyft) => {
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
      });
      return { ...prev, recent_shyfts: nextSignals };
    });
  }, [shyftMetaById]);

  const groupedShyfts = useMemo(
    () => (team ? groupSignalsByPlayerGame(team.recent_shyfts) : []),
    [team],
  );

  if (loading) return <LoadingState />;
  if (error || !team) return <EmptyState title="Team unavailable" copy={error ?? 'No team found.'} />;

  const isFollowed = profile?.follows.teams.includes(team.id) ?? team.is_followed;

  async function handleFollow() {
    if (!team) return;
    if (!currentUser) {
      openAuth('signin');
      return;
    }
    await toggleFollowTeam(team.id, isFollowed);
  }

  return (
    <div className="space-y-4">
      <section className="panel-surface px-5 py-5 sm:px-6">
        <nav className="mb-4 flex flex-wrap items-center gap-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
          <Link to="/teams" className="transition hover:text-ink">Teams</Link>
          <span className="text-white/20">/</span>
          <span className="text-ink">{team.name}</span>
        </nav>

        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0">
            <div className="eyebrow">Team Profile</div>
            <h1 className="mt-2 text-3xl font-semibold text-ink sm:text-4xl">{team.name}</h1>
            <p className="mt-2 max-w-3xl text-sm text-muted sm:text-[15px]">Track the latest shyfts tied to this team.</p>
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

        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <div className="rounded-[20px] bg-white/[0.03] px-4 py-4">
            <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">League</div>
            <div className="mt-2 text-2xl font-semibold text-ink">{team.league_name}</div>
          </div>
          <div className="rounded-[20px] bg-white/[0.03] px-4 py-4">
            <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">Active Shyfts</div>
            <div className="mt-2 text-2xl font-semibold text-ink">{team.shyft_count ?? team.recent_shyfts.length}</div>
          </div>
          <div className="rounded-[20px] bg-white/[0.03] px-4 py-4">
            <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">Tracked Players</div>
            <div className="mt-2 text-2xl font-semibold text-ink">{team.player_count}</div>
          </div>
        </div>
      </section>

      <TeamBoxScores rows={team.recent_box_scores} />

      <section className="panel-surface px-4 py-4">
        <SectionHeader
          title="Latest Shyfts"
          description="This page now leads with the newest team activity instead of roster browsing."
        />
        <div className="mt-4 space-y-4">
          {groupedShyfts.length === 0 ? (
            <div className="rounded-[20px] bg-white/[0.03] px-4 py-5 text-sm text-muted">
              No recent shyfts are active for this team yet.
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

      <section className="panel-surface px-4 py-4">
        <SectionHeader
          title="Players Live Elsewhere"
          description="Use the Players tab when you want roster-level exploration instead of the team shyft board."
        />
        <div className="mt-4 flex flex-col gap-3 rounded-[20px] bg-white/[0.03] px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-sm font-medium text-ink">Roster browsing has been moved out of this page.</div>
            <div className="mt-1 text-sm text-muted">
              {team.players.length > 0
                ? `${team.player_count} tracked players are available from the Players area.`
                : 'Tracked players will appear in the Players area when roster data is available.'}
            </div>
          </div>
          <Link
            to="/players"
            className="inline-flex items-center justify-center rounded-full border border-border bg-white/[0.04] px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-ink transition hover:border-borderStrong"
          >
            Open Players
          </Link>
        </div>
      </section>

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
            setTeam((prev) => {
              if (!prev) return prev;
              return {
                ...prev,
                recent_shyfts: prev.recent_shyfts.map((shyft) =>
                  ids.has(shyft.id) ? { ...shyft, comment_count: count } : shyft,
                ),
              };
            });
          }}
          onClose={() => setCommentThread(null)}
        />
      ) : null}
    </div>
  );
}
