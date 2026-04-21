import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { EmptyState } from '../components/EmptyState';
import { LoadingState } from '../components/LoadingState';
import { PageIntro } from '../components/PageIntro';
import { SectionHeader } from '../components/SectionHeader';
import { useSignalStore } from '../store/useSignalStore';

const LEAGUES = ['All', 'NBA', 'NFL'];

export function TeamsPage() {
  const { teams, loading, fetchTeams } = useSignalStore();
  const [leagueFilter, setLeagueFilter] = useState('All');
  const [query, setQuery] = useState('');

  useEffect(() => {
    void fetchTeams();
  }, [fetchTeams]);

  const filtered = useMemo(() => {
    const normalizedQuery = query.trim().toLowerCase();
    return teams.filter((team) => {
      const matchesLeague = leagueFilter === 'All' || team.league_name === leagueFilter;
      const matchesQuery = !normalizedQuery || team.name.toLowerCase().includes(normalizedQuery);
      return matchesLeague && matchesQuery;
    });
  }, [teams, leagueFilter, query]);

  if (loading) return <LoadingState />;
  if (!teams.length) {
    return <EmptyState title="No teams" copy="Seed the backend to populate the league directory." />;
  }

  return (
    <div className="space-y-4">
      <PageIntro
        eyebrow="Team Directory"
        title="Teams"
        description="Browse teams and see where signals are coming from. Pick a league, scan team activity, then open a team to drill into roster-level detail."
        aside={<div className="rounded-full bg-white/[0.04] px-4 py-2 text-xs uppercase tracking-[0.22em] text-[#ffd8bd]">{filtered.length} shown</div>}
      />

      <section className="panel-surface px-4 py-4">
        <SectionHeader
          title="Browse Teams"
          description="Search by team name or narrow the directory to one league."
        />

        <div className="mt-4 flex flex-col gap-3 lg:flex-row lg:items-center lg:justify-between">
          <input
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search teams"
            className="field-shell w-full max-w-[360px] px-4 py-3 text-sm placeholder:text-muted/70"
          />
          <div className="flex flex-wrap gap-2">
            {LEAGUES.map((league) => (
              <button
                key={league}
                type="button"
                onClick={() => setLeagueFilter(league)}
                className={`pill-button ${leagueFilter === league ? 'pill-button-active' : ''}`}
              >
                {league}
              </button>
            ))}
          </div>
        </div>
      </section>

      {filtered.length === 0 ? (
        <EmptyState title="No matches" copy="No teams match the current search and league filter." />
      ) : (
        <section className="panel-surface px-4 py-4">
          <SectionHeader
            title="Team Results"
            description="Teams are split by sport so each directory feels easier to scan."
          />
          <div className="mt-4 space-y-6">
            {(['NBA', 'NFL'] as const)
              .filter((league) => leagueFilter === 'All' || leagueFilter === league)
              .map((league) => {
                const leagueTeams = filtered.filter((team) => team.league_name === league);
                if (!leagueTeams.length) return null;

                return (
                  <div key={league} className="space-y-3">
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="text-xl font-semibold text-ink">{league}</h3>
                      <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
                        {leagueTeams.length} teams
                      </div>
                    </div>
                    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                      {leagueTeams.map((team) => {
                        const activityCount = team.signal_count ?? team.player_count;
                        return (
                          <Link
                            key={team.id}
                            to={`/teams/${team.id}`}
                            className="block rounded-[24px] bg-white/[0.02] px-4 py-4 transition hover:bg-white/[0.05]"
                          >
                            <div className="flex items-start justify-between gap-3">
                              <div>
                                <div className="text-xl font-semibold text-ink">{team.name}</div>
                                <div className="mt-1 text-sm text-muted">{team.league_name}</div>
                              </div>
                              <div className="h-2.5 w-2.5 rounded-full bg-accent shadow-[0_0_14px_rgba(249,115,22,0.45)]" />
                            </div>
                            <div className="mt-4 flex items-center justify-between text-sm">
                              <span className="text-muted">{activityCount} activity markers</span>
                              <span className="font-semibold text-[#ffd8bd]">Open team</span>
                            </div>
                          </Link>
                        );
                      })}
                    </div>
                  </div>
                );
              })}
          </div>
        </section>
      )}
    </div>
  );
}
