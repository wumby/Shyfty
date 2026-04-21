import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { EmptyState } from '../components/EmptyState';
import { LoadingState } from '../components/LoadingState';
import { PageIntro } from '../components/PageIntro';
import { SectionHeader } from '../components/SectionHeader';
import { SignalCard } from '../components/SignalCard';
import { useAuthStore } from '../store/useAuthStore';
import { useSignalStore } from '../store/useSignalStore';
import { api } from '../services/api';
import type { TeamDetail } from '../types';

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
      <PageIntro
        eyebrow="Team Profile"
        title={team.name}
        description="See which players are surfacing signals for this team, then drill into the roster or recent activity."
        breadcrumbs={[
          { label: 'Teams', to: '/teams' },
          { label: team.name },
        ]}
        aside={
          <button
            type="button"
            onClick={() => void handleFollow()}
            className={`rounded-full border px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] transition ${
              isFollowed
                ? 'border-accent/40 bg-accentSoft text-accent hover:bg-accent/20'
                : 'border-border bg-white/[0.04] text-muted hover:border-borderStrong hover:text-ink'
            }`}
          >
            {isFollowed ? '✓ Following' : '+ Follow team'}
          </button>
        }
      />

      <section className="panel-surface px-4 py-4">
        <SectionHeader
          title="Team Snapshot"
          description="Use this high-level summary to decide whether to inspect the roster or the latest signals next."
        />
        <div className="mt-4 grid gap-3 sm:grid-cols-3">
          <div className="rounded-[20px] bg-white/[0.03] px-4 py-4">
            <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">League</div>
            <div className="mt-2 text-2xl font-semibold text-ink">{team.league_name}</div>
          </div>
          <div className="rounded-[20px] bg-white/[0.03] px-4 py-4">
            <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">Tracked Players</div>
            <div className="mt-2 text-2xl font-semibold text-ink">{team.player_count}</div>
          </div>
          <div className="rounded-[20px] bg-white/[0.03] px-4 py-4">
            <div className="text-[10px] font-semibold uppercase tracking-[0.16em] text-muted">Recent Signals</div>
            <div className="mt-2 text-2xl font-semibold text-ink">{team.recent_signals.length}</div>
          </div>
        </div>
      </section>

      <div className="grid gap-4 lg:grid-cols-[320px,minmax(0,1fr)]">
        <section className="panel-surface px-4 py-4">
          <SectionHeader
            title="Roster"
            description="Open any player profile to move from team context into individual analysis."
          />
          {team.players.length === 0 ? (
            <div className="mt-4 rounded-[20px] bg-white/[0.03] px-4 py-5 text-sm text-muted">
              No tracked players are available for this team yet.
            </div>
          ) : (
            <div className="mt-4 space-y-2">
              {team.players.map((player) => (
                <Link
                  key={player.id}
                  to={`/players/${player.id}`}
                  className="flex items-center justify-between rounded-[18px] bg-white/[0.02] px-3 py-3 text-sm transition hover:bg-white/[0.05]"
                >
                  <div>
                    <div className="font-medium text-ink">{player.name}</div>
                    <div className="mt-1 text-xs text-muted">{player.position}</div>
                  </div>
                  <span className="font-semibold text-[#ffd8bd]">Open</span>
                </Link>
              ))}
            </div>
          )}
        </section>

        <section className="panel-surface px-4 py-4">
          <SectionHeader
            title="Recent Signals"
            description="Start here to understand what is currently driving attention on this team."
          />
          <div className="mt-4">
            {team.recent_signals.length === 0 ? (
              <div className="rounded-[20px] bg-white/[0.03] px-4 py-5 text-sm text-muted">
                No recent signals are active for this team. Browse the roster to inspect player profiles directly.
              </div>
            ) : (
              <div className="space-y-2">
                {team.recent_signals.map((signal) => (
                  <SignalCard key={signal.id} signal={signal} />
                ))}
              </div>
            )}
          </div>
        </section>
      </div>
    </div>
  );
}
