import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { EmptyState } from '../components/EmptyState';
import { LoadingState } from '../components/LoadingState';
import { useSignalStore } from '../store/useSignalStore';

const LEAGUES = ['All', 'NBA', 'NFL'];

export function TeamsPage() {
  const { teams, loading, fetchTeams } = useSignalStore();
  const [leagueFilter, setLeagueFilter] = useState('All');

  useEffect(() => {
    void fetchTeams();
  }, [fetchTeams]);

  if (loading) return <LoadingState />;
  if (!teams.length) return <EmptyState title="No teams" copy="Seed the backend to populate the league directory." />;

  const filtered = leagueFilter === 'All' ? teams : teams.filter((t) => t.league_name === leagueFilter);

  return (
    <div className="space-y-4">
      <div className="panel-surface hero-grid px-5 py-5">
        <div className="eyebrow">Team Directory</div>
        <div className="mt-2 flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div>
            <h1 className="text-4xl font-semibold text-ink">Follow team environments, not isolated names.</h1>
            <p className="mt-2 max-w-2xl text-sm text-muted">Browse organizations, compare roster coverage, and open team pages to see who is driving the latest activity.</p>
          </div>
          <div className="rounded-full border border-border bg-white/[0.04] px-4 py-2 text-xs uppercase tracking-[0.22em] text-[#ffd8bd]">
            {filtered.length} shown
          </div>
        </div>
      </div>

      <div className="flex flex-wrap items-center gap-2">
        {LEAGUES.map((league) => (
          <button
            key={league}
            type="button"
            onClick={() => setLeagueFilter(league)}
            className={`pill-button ${
              leagueFilter === league
                ? 'pill-button-active'
                : ''
            }`}
          >
            {league}
          </button>
        ))}
      </div>

      {filtered.length === 0 ? (
        <EmptyState title={`No ${leagueFilter} teams`} copy="Try a different league filter." />
      ) : (
        <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
          {filtered.map((team) => (
            <Link
              key={team.id}
              to={`/teams/${team.id}`}
              className="panel-surface block p-5 transition hover:-translate-y-0.5 hover:border-borderStrong hover:bg-white/[0.05]"
            >
              <div className="eyebrow text-[#ffd8bd]">{team.league_name}</div>
              <div className="mt-2 text-2xl font-semibold text-ink">{team.name}</div>
              <div className="mt-4 inline-flex rounded-full border border-border bg-white/[0.03] px-3 py-1 text-xs uppercase tracking-[0.25em] text-muted">
                {team.player_count} tracked {team.player_count === 1 ? 'player' : 'players'}
              </div>
            </Link>
          ))}
        </div>
      )}
    </div>
  );
}
