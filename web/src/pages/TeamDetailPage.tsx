import { useEffect, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { EmptyState } from '../components/EmptyState';
import { LoadingState } from '../components/LoadingState';
import { SignalCard } from '../components/SignalCard';
import { api } from '../services/api';
import type { TeamDetail } from '../types';

export function TeamDetailPage() {
  const { id = '' } = useParams();
  const [team, setTeam] = useState<TeamDetail | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null);

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

  return (
    <div className="space-y-4">
      <div className="panel-surface hero-grid p-6">
        <div className="eyebrow text-[#ffd8bd]">{team.league_name}</div>
        <div className="mt-3 flex flex-col gap-3 sm:flex-row sm:items-end sm:justify-between">
          <h2 className="text-4xl font-semibold text-ink">{team.name}</h2>
          <div className="rounded-[22px] border border-border bg-white/[0.04] px-4 py-2 text-sm text-muted">
            {team.player_count} tracked {team.player_count === 1 ? 'player' : 'players'}
          </div>
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-[240px,minmax(0,1fr)]">
        <div className="panel-surface p-4">
          <div className="eyebrow mb-3">Roster</div>
          {team.players.length === 0 ? (
            <p className="text-sm text-muted">No players tracked.</p>
          ) : (
            <div className="flex flex-col gap-1">
              {team.players.map((player) => (
                <Link
                  key={player.id}
                  to={`/players/${player.id}`}
                  className="flex items-center justify-between rounded-[18px] px-3 py-2.5 text-sm transition hover:bg-white/[0.04]"
                >
                  <span className="font-medium text-ink">{player.name}</span>
                  <span className="text-xs text-muted">{player.position}</span>
                </Link>
              ))}
            </div>
          )}
        </div>

        <div className="overflow-hidden">
          <div className="mb-3 px-1">
            <div className="eyebrow">
              Recent Signals · {team.recent_signals.length}
            </div>
          </div>
          {team.recent_signals.length === 0 ? (
            <EmptyState title="No signals yet" copy="Signals will appear as player data is ingested." />
          ) : (
            <div>
              {team.recent_signals.map((signal) => (
                <SignalCard key={signal.id} signal={signal} />
              ))}
            </div>
          )}
        </div>
      </div>
    </div>
  );
}
