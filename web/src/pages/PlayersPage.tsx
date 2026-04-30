import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { EmptyState } from '../components/EmptyState';
import { LoadingState } from '../components/LoadingState';
import { SearchInput } from '../components/SearchInput';
import { SectionHeader } from '../components/SectionHeader';
import { useSignalStore } from '../store/useSignalStore';

const LEAGUES = ['All', 'NBA', 'NFL'] as const;

export function PlayersPage() {
  const { players, loading, fetchPlayers } = useSignalStore();
  const [query, setQuery] = useState('');
  const [teamFilter, setTeamFilter] = useState('');
  const [positionFilter, setPositionFilter] = useState('');
  const [leagueFilter, setLeagueFilter] = useState<(typeof LEAGUES)[number]>('All');

  useEffect(() => {
    void fetchPlayers();
  }, [fetchPlayers]);

  const teams = useMemo(() => [...new Set(players.map((player) => player.team_name))].sort(), [players]);
  const positions = useMemo(() => [...new Set(players.map((player) => player.position))].sort(), [players]);

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    return players.filter((player) => {
      const matchesQuery =
        !q ||
        player.name.toLowerCase().includes(q) ||
        player.team_name.toLowerCase().includes(q) ||
        player.position.toLowerCase().includes(q);
      const matchesLeague = leagueFilter === 'All' || player.league_name === leagueFilter;
      const matchesTeam = !teamFilter || player.team_name === teamFilter;
      const matchesPosition = !positionFilter || player.position === positionFilter;
      return matchesQuery && matchesLeague && matchesTeam && matchesPosition;
    });
  }, [players, query, teamFilter, positionFilter, leagueFilter]);

  const grouped = useMemo(
    () => ({
      NBA: filtered.filter((player) => player.league_name === 'NBA'),
      NFL: filtered.filter((player) => player.league_name === 'NFL'),
    }),
    [filtered],
  );

  if (loading) return <LoadingState />;
  if (!players.length) {
    return <EmptyState title="No players yet" copy="No live player data has been synced yet. Run a bootstrap or incremental sync to populate the directory." />;
  }

  return (
    <div className="space-y-4">
      <section className="panel-surface relative z-10 px-5 py-5 sm:px-6">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-end lg:justify-between">
          <div className="min-w-0">
            <div className="eyebrow">Player Directory</div>
            <h1 className="mt-2 text-3xl font-semibold text-ink sm:text-4xl">Players</h1>
            <p className="mt-2 max-w-3xl text-sm text-muted sm:text-[15px]">Search by name, or filter by team and position to browse the field.</p>
          </div>
          <div className="shrink-0">
            <div className="rounded-full bg-white/[0.04] px-4 py-2 text-xs uppercase tracking-[0.22em] text-[#ffd8bd]">{filtered.length} shown</div>
          </div>
        </div>

        <div className="mt-5 grid gap-3 lg:grid-cols-[minmax(0,1fr),180px,180px,180px]">
          <SearchInput
            value={query}
            players={players}
            onChange={setQuery}
            placeholder="Search players, teams, or positions"
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
          <select
            value={teamFilter}
            onChange={(event) => setTeamFilter(event.target.value)}
            className="field-shell px-3 py-2 text-sm"
          >
            <option value="">All teams</option>
            {teams.map((team) => (
              <option key={team} value={team}>{team}</option>
            ))}
          </select>
          <select
            value={positionFilter}
            onChange={(event) => setPositionFilter(event.target.value)}
            className="field-shell px-3 py-2 text-sm"
          >
            <option value="">All positions</option>
            {positions.map((position) => (
              <option key={position} value={position}>{position}</option>
            ))}
          </select>
        </div>
      </section>

      {filtered.length === 0 ? (
        <EmptyState title="No matches" copy="No players match the current search and filters." />
      ) : (
        <section className="panel-surface px-4 py-4">
          <SectionHeader
            title="Player Results"
            description="Players are split by sport so it is easier to browse the league you care about."
          />
          <div className="mt-4 space-y-6">
            {(['NBA', 'NFL'] as const)
              .filter((league) => leagueFilter === 'All' || leagueFilter === league)
              .map((league) =>
                grouped[league].length ? (
                  <div key={league} className="space-y-3">
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="text-xl font-semibold text-ink">{league}</h3>
                      <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
                        {grouped[league].length} players
                      </div>
                    </div>
                    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-4">
                      {grouped[league].map((player) => (
                        <Link
                          key={player.id}
                          to={`/players/${player.id}`}
                          className="group grid w-full grid-cols-[minmax(0,1fr)_auto] items-center gap-x-4 rounded-[18px] border border-white/[0.06] bg-white/[0.02] px-3 py-3 transition hover:border-white/[0.1] hover:bg-white/[0.055]"
                        >
                          <span className="min-w-0">
                            <span className="block truncate text-[17px] font-bold leading-tight text-ink">{player.name}</span>
                            <span className="mt-0.5 flex items-center gap-2 text-[12px] text-muted">
                              <span>{player.team_name} · {player.position}</span>
                              {(player.signal_count ?? 0) > 0 ? (
                                <>
                                  <span className="text-white/15">•</span>
                                  <span>{player.signal_count} signal{player.signal_count !== 1 ? 's' : ''}</span>
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
                      ))}
                    </div>
                  </div>
                ) : null,
              )}
          </div>
        </section>
      )}
    </div>
  );
}
