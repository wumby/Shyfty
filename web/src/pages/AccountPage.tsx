import { useEffect } from 'react';
import { useNavigate } from 'react-router-dom';

import { useAuthStore } from '../store/useAuthStore';
import { useSignalStore } from '../store/useSignalStore';

export function AccountPage() {
  const navigate = useNavigate();
  const currentUser = useAuthStore((state) => state.currentUser);
  const openAuth = useAuthStore((state) => state.openAuth);
  const signOut = useAuthStore((state) => state.signOut);
  const {
    profile,
    players,
    teams,
    fetchProfile,
    fetchPlayers,
    fetchTeams,
    toggleFollowPlayer,
    toggleFollowTeam,
    deleteSavedView,
    setFilters,
  } = useSignalStore();

  useEffect(() => {
    if (!currentUser) return;
    void fetchProfile();
    if (!players.length) void fetchPlayers();
    if (!teams.length) void fetchTeams();
  }, [currentUser, fetchProfile, fetchPlayers, fetchTeams, players.length, teams.length]);

  if (!currentUser) {
    return (
      <div className="panel-surface px-6 py-8 text-center">
        <p className="text-sm text-muted">Sign in to manage follows, saved views, and account settings.</p>
        <button
          type="button"
          onClick={() => openAuth('signin')}
          className="mt-4 rounded-full bg-accent px-5 py-2 text-sm font-semibold text-white"
        >
          Sign In
        </button>
      </div>
    );
  }

  const followedPlayers = players.filter((p) => profile?.follows.players.includes(p.id));
  const followedTeams = teams.filter((t) => profile?.follows.teams.includes(t.id));
  const hasFollows = followedPlayers.length > 0 || followedTeams.length > 0;
  const hasSavedViews = (profile?.saved_views.length ?? 0) > 0;

  return (
    <div className="space-y-4">
      <section className="panel-surface px-5 py-4">
        <div className="flex items-center justify-between gap-4">
          <div className="min-w-0">
            <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted">Account</div>
            <div className="mt-1 truncate text-sm font-semibold text-ink">{currentUser.email}</div>
          </div>
          <button
            type="button"
            onClick={() => void signOut()}
            className="shrink-0 rounded-full border border-border px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.14em] text-muted transition hover:border-borderStrong hover:text-ink"
          >
            Sign Out
          </button>
        </div>
      </section>

      <section className="panel-surface px-5 py-5">
        <div className="mb-4 flex items-center justify-between">
          <h2 className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted">Following</h2>
          {hasFollows ? (
            <span className="text-[11px] text-muted">{followedPlayers.length + followedTeams.length} tracked</span>
          ) : null}
        </div>

        {hasFollows ? (
          <div className="space-y-2">
            {followedPlayers.map((player) => (
              <div key={player.id} className="flex items-center justify-between gap-4 rounded-[18px] border border-border bg-white/[0.025] px-4 py-3">
                <div className="min-w-0">
                  <button type="button" onClick={() => navigate(`/players/${player.id}`)} className="truncate text-sm font-semibold text-ink hover:text-accent">
                    {player.name}
                  </button>
                  <div className="mt-0.5 text-xs text-muted">{player.team_name} · {player.position} · {player.league_name}</div>
                </div>
                <button type="button" onClick={() => void toggleFollowPlayer(player.id, true)} className="shrink-0 text-[11px] font-semibold text-muted transition hover:text-danger">
                  Unfollow
                </button>
              </div>
            ))}
            {followedTeams.map((team) => (
              <div key={team.id} className="flex items-center justify-between gap-4 rounded-[18px] border border-border bg-white/[0.025] px-4 py-3">
                <div className="min-w-0">
                  <span className="truncate text-sm font-semibold text-ink">{team.name}</span>
                  <div className="mt-0.5 text-xs text-muted">{team.league_name}</div>
                </div>
                <button type="button" onClick={() => void toggleFollowTeam(team.id, true)} className="shrink-0 text-[11px] font-semibold text-muted transition hover:text-danger">
                  Unfollow
                </button>
              </div>
            ))}
          </div>
        ) : (
          <p className="text-sm text-muted">
            You're not following anyone yet.{' '}
            <button type="button" onClick={() => navigate('/players')} className="text-accent underline-offset-2 hover:underline">
              Browse players
            </button>
          </p>
        )}
      </section>

      {hasSavedViews ? (
        <section className="panel-surface px-5 py-5">
          <h2 className="mb-4 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted">Saved Views</h2>
          <div className="space-y-2">
            {profile!.saved_views.map((view) => (
              <div key={view.id} className="flex items-center justify-between gap-4 rounded-[18px] border border-border bg-white/[0.025] px-4 py-3">
                <div className="min-w-0">
                  <div className="truncate text-sm font-semibold text-ink">{view.name}</div>
                  <div className="mt-0.5 text-xs text-muted">{[view.league, view.signal_type].filter(Boolean).join(' · ') || 'All signals'}</div>
                </div>
                <div className="flex shrink-0 items-center gap-3">
                  <button
                    type="button"
                    onClick={() => {
                      setFilters({
                        league: view.league ?? undefined,
                        signal_type: view.signal_type ?? undefined,
                        player: view.player ?? undefined,
                        sort: view.sort_mode,
                        feed: view.feed_mode,
                      });
                      navigate('/');
                    }}
                    className="text-[11px] font-semibold text-accent transition hover:brightness-110"
                  >
                    Open
                  </button>
                  <button type="button" onClick={() => void deleteSavedView(view.id)} className="text-[11px] font-semibold text-muted transition hover:text-danger">
                    Delete
                  </button>
                </div>
              </div>
            ))}
          </div>
        </section>
      ) : null}
    </div>
  );
}
