import { useEffect } from 'react';

import { useAuthStore } from '../store/useAuthStore';
import { useSignalStore } from '../store/useSignalStore';

export function ProfilePage() {
  const currentUser = useAuthStore((state) => state.currentUser);
  const openAuth = useAuthStore((state) => state.openAuth);
  const signOut = useAuthStore((state) => state.signOut);
  const { profile, fetchProfile, updatePreferences, deleteSavedView, setFilters } = useSignalStore();

  useEffect(() => {
    if (currentUser) void fetchProfile();
  }, [currentUser, fetchProfile]);

  if (!currentUser) {
    return (
      <div className="panel-surface px-6 py-8">
        <div className="eyebrow">Personalization</div>
        <h2 className="mt-3 text-2xl font-semibold text-ink">Sign in to save board presets, follows, and notification settings.</h2>
        <button
          type="button"
          onClick={() => openAuth('signin')}
          className="mt-5 rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white"
        >
          Sign In
        </button>
      </div>
    );
  }

  return (
    <div className="space-y-3">
      <section className="panel-surface px-5 py-5">
        <div className="eyebrow">Profile</div>
        <h2 className="mt-2 text-2xl font-semibold text-ink">{currentUser.email}</h2>
        <p className="mt-1 text-sm text-muted">Tune the default board behavior and keep reusable views in one place.</p>
        <button
          type="button"
          onClick={() => void signOut()}
          className="mt-4 rounded-full border border-border px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-muted transition hover:text-ink"
        >
          Sign Out
        </button>
      </section>

      <section className="panel-surface px-5 py-5">
        <div className="eyebrow">Preferences</div>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <label className="text-sm text-muted">
            Preferred league
            <select
              value={profile?.preferences.preferred_league ?? ''}
              onChange={(event) => void updatePreferences({ preferred_league: event.target.value || null })}
              className="mt-2 w-full rounded-2xl border border-border bg-white/[0.03] px-3 py-2 text-ink"
            >
              <option value="">All leagues</option>
              <option value="NBA">NBA</option>
              <option value="NFL">NFL</option>
            </select>
          </label>
          <label className="text-sm text-muted">
            Default feed
            <select
              value={profile?.preferences.default_feed_mode ?? 'all'}
              onChange={(event) => void updatePreferences({ default_feed_mode: event.target.value as 'all' | 'following' | 'for_you' })}
              className="mt-2 w-full rounded-2xl border border-border bg-white/[0.03] px-3 py-2 text-ink"
            >
              <option value="all">All</option>
              <option value="following">Following</option>
              <option value="for_you">For You</option>
            </select>
          </label>
          <label className="flex items-center justify-between rounded-2xl border border-border bg-white/[0.02] px-4 py-3 text-sm text-muted">
            Daily digest scaffolding
            <input
              type="checkbox"
              checked={profile?.preferences.notification_digest ?? false}
              onChange={(event) => void updatePreferences({ notification_digest: event.target.checked })}
            />
          </label>
          <label className="flex items-center justify-between rounded-2xl border border-border bg-white/[0.02] px-4 py-3 text-sm text-muted">
            Release/alert scaffolding
            <input
              type="checkbox"
              checked={profile?.preferences.notification_releases ?? false}
              onChange={(event) => void updatePreferences({ notification_releases: event.target.checked })}
            />
          </label>
        </div>
      </section>

      <section className="panel-surface px-5 py-5">
        <div className="eyebrow">Saved Views</div>
        <div className="mt-4 space-y-3">
          {profile?.saved_views.length ? profile.saved_views.map((view) => (
            <div key={view.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl border border-border bg-white/[0.02] px-4 py-3">
              <div>
                <div className="text-sm font-semibold text-ink">{view.name}</div>
                <div className="mt-1 text-xs text-muted">
                  {(view.feed_mode ?? 'all').replace(/_/g, ' ')} · {(view.sort_mode ?? 'newest').replace(/_/g, ' ')}
                </div>
              </div>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => setFilters({
                    league: view.league ?? undefined,
                    signal_type: view.signal_type ?? undefined,
                    player: view.player ?? undefined,
                    sort: view.sort_mode,
                    feed: view.feed_mode,
                  })}
                  className="rounded-full border border-border px-3 py-1.5 text-[10px] uppercase tracking-[0.14em] text-muted transition hover:text-ink"
                >
                  Apply
                </button>
                <button
                  type="button"
                  onClick={() => void deleteSavedView(view.id)}
                  className="rounded-full border border-border px-3 py-1.5 text-[10px] uppercase tracking-[0.14em] text-muted transition hover:text-danger"
                >
                  Delete
                </button>
              </div>
            </div>
          )) : (
            <p className="text-sm text-muted">Save a feed view from the main board to pin it here.</p>
          )}
        </div>
      </section>
    </div>
  );
}
