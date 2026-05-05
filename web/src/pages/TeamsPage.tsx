import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { EmptyState } from '../components/EmptyState';
import { LoadingState } from '../components/LoadingState';
import { SectionHeader } from '../components/SectionHeader';
import { useShyftStore } from "../store/useShyftStore";

const LEAGUES = ['All', 'NBA', 'NFL'] as const;

export function TeamsPage() {
  const { teams, loading, fetchTeams } = useShyftStore();
  const [leagueFilter, setLeagueFilter] = useState<(typeof LEAGUES)[number]>('All');
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
    return <EmptyState title="No teams yet" copy="No live team data has been synced yet. Run a bootstrap or incremental sync to populate the directory." />;
  }

  return (
    <div className="space-y-4">
      <section className="panel-surface relative z-10 px-5 py-5 sm:px-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0">
            <div className="eyebrow">Team Directory</div>
            <h1 className="mt-2 text-3xl font-semibold text-ink sm:text-4xl">Teams</h1>
            <p className="mt-2 max-w-3xl text-sm text-muted sm:text-[15px]">Search by team name or narrow to one league.</p>
          </div>
          <div className="shrink-0">
            <div className="rounded-full bg-white/[0.04] px-4 py-2 text-xs uppercase tracking-[0.22em] text-[#ffd8bd]">{filtered.length} shown</div>
          </div>
        </div>

        <div className="mt-5 grid gap-3 sm:grid-cols-[minmax(0,1fr),180px]">
          <input
            type="text"
            value={query}
            onChange={(event) => setQuery(event.target.value)}
            placeholder="Search teams"
            className="field-shell px-4 py-2 text-sm placeholder:text-muted/70"
          />
          <select
            value={leagueFilter}
            onChange={(event) => setLeagueFilter(event.target.value as (typeof LEAGUES)[number])}
            className="field-shell px-3 py-2 text-sm"
          >
            {LEAGUES.map((league) => (
              <option key={league} value={league}>{league === 'All' ? 'All Sports' : league}</option>
            ))}
          </select>
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
                    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                      {leagueTeams.map((team) => {
                        const activityCount = team.shyft_count ?? team.player_count;
                        return (
                          <Link
                            key={team.id}
                            to={`/teams/${team.id}`}
                            className="group grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 rounded-[18px] border border-white/[0.06] bg-white/[0.02] px-3 py-3 transition hover:border-white/[0.1] hover:bg-white/[0.055]"
                          >
                            <span className="min-w-0">
                              <span className="block truncate text-[17px] font-bold leading-tight text-ink">{team.name}</span>
                              <span className="mt-0.5 flex items-center gap-2 text-[12px] text-muted">
                                <span>{team.league_name}</span>
                                {activityCount ? (
                                  <>
                                    <span className="text-white/15">•</span>
                                    <span>{activityCount} shyft{activityCount !== 1 ? 's' : ''}</span>
                                  </>
                                ) : null}
                              </span>
                            </span>
                            <span className="flex h-7 w-7 shrink-0 items-center justify-center rounded-full border border-white/[0.08] bg-white/[0.03] text-muted transition group-hover:border-accent/40 group-hover:bg-accent/10 group-hover:text-[#ffd8bd]">
                              <svg width="12" height="12" viewBox="0 0 12 12" fill="none" aria-hidden="true">
                                <path d="M4.5 2.5L8 6L4.5 9.5" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
                              </svg>
                            </span>
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
