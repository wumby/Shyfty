import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { EmptyState } from '../components/EmptyState';
import { LoadingState } from '../components/LoadingState';
import { useSignalStore } from '../store/useSignalStore';

export function PlayersPage() {
  const { players, loading, fetchPlayers } = useSignalStore();
  const [query, setQuery] = useState('');

  useEffect(() => {
    void fetchPlayers();
  }, [fetchPlayers]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return players;
    return players.filter(
      (p) =>
        p.name.toLowerCase().includes(q) ||
        p.team_name.toLowerCase().includes(q) ||
        p.position.toLowerCase().includes(q),
    );
  }, [players, query]);

  if (loading) return <LoadingState />;
  if (!players.length) return <EmptyState title="No players" copy="Seed the backend to populate the player directory." />;

  return (
    <div className="space-y-4">
      <div className="panel-surface hero-grid px-5 py-5">
        <div className="eyebrow">Player Directory</div>
        <div className="mt-2 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-4xl font-semibold text-ink">Scan player profiles with live context.</h1>
            <p className="mt-2 max-w-2xl text-sm text-muted">Search across teams, positions, and leagues, then drill into trend history and active signal volume.</p>
          </div>
          <div className="rounded-full border border-border bg-white/[0.04] px-4 py-2 text-xs uppercase tracking-[0.22em] text-[#ffd8bd]">
            {filtered.length} shown
          </div>
        </div>
      </div>

      <div className="relative">
        <input
          type="text"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search players, teams, positions…"
          className="field-shell w-full px-4 py-3 text-sm placeholder:text-muted/70"
        />
        {query && (
          <button
            type="button"
            onClick={() => setQuery('')}
            className="absolute right-4 top-1/2 -translate-y-1/2 text-muted transition hover:text-ink"
          >
            ✕
          </button>
        )}
      </div>

      {filtered.length === 0 ? (
        <EmptyState title="No matches" copy={`No players match "${query}".`} />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((player) => (
            <Link
              key={player.id}
              to={`/players/${player.id}`}
              className="panel-surface block p-5 transition hover:-translate-y-0.5 hover:border-borderStrong hover:bg-white/[0.05]"
            >
              <div className="eyebrow text-[#ffd8bd]">{player.league_name}</div>
              <div className="mt-2 text-2xl font-semibold text-ink">{player.name}</div>
              <div className="mt-1 text-sm text-muted">{player.team_name}</div>
              <div className="mt-4 inline-flex rounded-full border border-border bg-white/[0.03] px-3 py-1 text-xs uppercase tracking-[0.25em] text-muted">{player.position}</div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
