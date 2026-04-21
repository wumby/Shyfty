import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { EmptyState } from '../components/EmptyState';
import { LoadingState } from '../components/LoadingState';
import { PageIntro } from '../components/PageIntro';
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

  const groupedPlayers = useMemo(
    () => ({
      NBA: filtered.filter((player) => player.league_name === 'NBA'),
      NFL: filtered.filter((player) => player.league_name === 'NFL'),
    }),
    [filtered],
  );

  if (loading) return <LoadingState />;
  if (!players.length) {
    return <EmptyState title="No players" copy="Seed the backend to populate the player directory." />;
  }

  return (
    <div className="space-y-4">
      <PageIntro
        eyebrow="Player Directory"
        title="Players"
        description="Find a player and analyze performance. Search first, narrow by team or position, then open a player profile to drill deeper."
        aside={<div className="rounded-full bg-white/[0.04] px-4 py-2 text-xs uppercase tracking-[0.22em] text-[#ffd8bd]">{filtered.length} shown</div>}
      />

      <section className="panel-surface px-4 py-4">
        <SectionHeader
          title="Find A Player"
          description="Use search when you know the name, or filter by team and position to browse the field."
        />

        <div className="mt-4 grid gap-3 lg:grid-cols-[minmax(0,1fr),220px,220px]">
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
              <option key={league} value={league}>{league}</option>
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
        </div>
        <div className="mt-3 max-w-[220px]">
          <select
            value={positionFilter}
            onChange={(event) => setPositionFilter(event.target.value)}
            className="field-shell w-full px-3 py-2 text-sm"
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
                groupedPlayers[league].length ? (
                  <div key={league} className="space-y-3">
                    <div className="flex items-center justify-between gap-3">
                      <h3 className="text-xl font-semibold text-ink">{league}</h3>
                      <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
                        {groupedPlayers[league].length} players
                      </div>
                    </div>
                    <div className="grid gap-3 md:grid-cols-2 xl:grid-cols-3">
                      {groupedPlayers[league].map((player) => (
                        <Link
                          key={player.id}
                          to={`/players/${player.id}`}
                          className="block rounded-[24px] bg-white/[0.02] px-4 py-4 transition hover:bg-white/[0.05]"
                        >
                          <div className="flex items-start justify-between gap-3">
                            <div>
                              <div className="text-xl font-semibold text-ink">{player.name}</div>
                              <div className="mt-1 text-sm text-muted">{player.team_name} · {player.position}</div>
                            </div>
                            <div className="text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">{player.league_name}</div>
                          </div>
                          <div className="mt-4 flex items-center justify-between text-sm">
                            <span className="text-muted">{player.signal_count ?? 0} active signals</span>
                            <span className="font-semibold text-[#ffd8bd]">Open profile</span>
                          </div>
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
