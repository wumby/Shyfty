import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { EmptyState } from '../components/EmptyState';
import { LastGameSignalCard } from '../components/LastGameSignalCard';
import { LoadingState } from '../components/LoadingState';
import { SectionHeader } from '../components/SectionHeader';
import { SignalDetailDrawer } from '../components/SignalDetailDrawer';
import { useAuthStore } from '../store/useAuthStore';
import { useSignalStore } from '../store/useSignalStore';
import { api } from '../services/api';
import type { Signal, TeamDetail } from '../types';

function groupSignalsByPlayerGame(signals: Signal[]): Signal[][] {
  const grouped = new Map<string, Signal[]>();
  for (const signal of signals) {
    const key = `${signal.player_id ?? signal.team_id}:${signal.game_id ?? signal.event_date ?? 'unknown'}`;
    const existing = grouped.get(key);
    if (existing) existing.push(signal);
    else grouped.set(key, [signal]);
  }
  return [...grouped.values()];
}

export function TeamDetailPage() {
  const { id = '' } = useParams();
  const currentUser = useAuthStore((state) => state.currentUser);
  const openAuth = useAuthStore((state) => state.openAuth);
  const fetchProfile = useSignalStore((state) => state.fetchProfile);
  const toggleFollowTeam = useSignalStore((state) => state.toggleFollowTeam);
  const profile = useSignalStore((state) => state.profile);
  const [team, setTeam] = useState<TeamDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);
  const [detailSignalId, setDetailSignalId] = useState<number | null>(null);

  useEffect(() => {
    if (!currentUser) return;
    void fetchProfile();
  }, [currentUser, fetchProfile]);

  useEffect(() => {
    async function load() {
      setLoading(true);
      setError(null);
      try {
        setTeam(await api.getTeam(id));
      } catch (err) {
        setError(err instanceof Error ? err.message : 'Unknown error');
      } finally {
        setLoading(false);
      }
    }

    void load();
  }, [id]);

  const groupedSignals = useMemo(
    () => (team ? groupSignalsByPlayerGame(team.recent_signals) : []),
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
            <p className="mt-2 max-w-3xl text-sm text-muted sm:text-[15px]">Track the latest signals tied to this team.</p>
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
            {isFollowed ? '✓ Following' : '+ Follow team'}
          </button>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-3">
          <div className="rounded-[20px] bg-white/[0.03] px-4 py-4">
            <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">League</div>
            <div className="mt-2 text-2xl font-semibold text-ink">{team.league_name}</div>
          </div>
          <div className="rounded-[20px] bg-white/[0.03] px-4 py-4">
            <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">Active Signals</div>
            <div className="mt-2 text-2xl font-semibold text-ink">{team.signal_count ?? team.recent_signals.length}</div>
          </div>
          <div className="rounded-[20px] bg-white/[0.03] px-4 py-4">
            <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">Tracked Players</div>
            <div className="mt-2 text-2xl font-semibold text-ink">{team.player_count}</div>
          </div>
        </div>
      </section>

      <section className="panel-surface px-4 py-4">
        <SectionHeader
          title="Latest Signals"
          description="This page now leads with the newest team activity instead of roster browsing."
        />
        <div className="mt-4 space-y-4">
          {groupedSignals.length === 0 ? (
            <div className="rounded-[20px] bg-white/[0.03] px-4 py-5 text-sm text-muted">
              No recent signals are active for this team yet.
            </div>
          ) : (
            groupedSignals.map((group) => (
              <LastGameSignalCard
                key={`${group[0]?.player_id ?? group[0]?.team_id ?? 'unknown'}-${group[0]?.game_id ?? group[0]?.event_date ?? 'game'}`}
                signals={group}
                onOpenDetail={(signalId) => setDetailSignalId(signalId)}
              />
            ))
          )}
        </div>
      </section>

      <section className="panel-surface px-4 py-4">
        <SectionHeader
          title="Players Live Elsewhere"
          description="Use the Players tab when you want roster-level exploration instead of the team signal board."
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

      {detailSignalId != null ? (
        <SignalDetailDrawer signalId={detailSignalId} onClose={() => setDetailSignalId(null)} />
      ) : null}
    </div>
  );
}
