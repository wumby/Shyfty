import { useEffect } from 'react';

import { PageIntro } from '../components/PageIntro';
import { SectionHeader } from '../components/SectionHeader';
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
      <div className="space-y-4">
        <PageIntro
          eyebrow="Account"
          title="Profile"
          description="Sign in to manage preferences, saved views, and the follow-based defaults that shape your experience."
        />
        <section className="panel-surface px-6 py-8">
          <SectionHeader
            title="Account Info"
            description="You need an account to save views, follow players or teams, and keep your preferred defaults."
          />
          <button
            type="button"
            onClick={() => openAuth('signin')}
            className="mt-5 rounded-full bg-accent px-4 py-2 text-sm font-semibold text-white"
          >
            Sign In
          </button>
        </section>
      </div>
    );
  }

  return (
    <div className="space-y-4">
      <PageIntro
        eyebrow="Account"
        title="Profile"
        description="Manage your account info, choose how Shyfty opens by default, and reuse the views you care about most."
      />

      <section className="panel-surface px-5 py-5">
        <SectionHeader
          title="Account Info"
          description="Basic account details and session controls."
        />
        <div className="mt-4 flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between">
          <div>
            <div className="text-lg font-semibold text-ink">{currentUser.email}</div>
            <div className="mt-1 text-sm text-muted">Signed in and ready to personalize the app.</div>
          </div>
          <button
            type="button"
            onClick={() => void signOut()}
            className="rounded-full border border-border px-4 py-2 text-xs font-semibold uppercase tracking-[0.16em] text-muted transition hover:text-ink"
          >
            Sign Out
          </button>
        </div>
      </section>

      <section className="panel-surface px-5 py-5">
        <SectionHeader
          title="Preferences"
          description="Choose the defaults that should shape your feed and notifications."
        />
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <label className="text-sm text-muted">
            Preferred league
            <select
              value={profile?.preferences.preferred_league ?? ''}
              onChange={(event) => void updatePreferences({ preferred_league: event.target.value || null })}
              className="field-shell mt-2 w-full px-3 py-2 text-ink"
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
              className="field-shell mt-2 w-full px-3 py-2 text-ink"
            >
              <option value="all">All</option>
              <option value="following">Following</option>
              <option value="for_you">For You</option>
            </select>
          </label>

          <label className="flex items-center justify-between rounded-2xl bg-white/[0.02] px-4 py-3 text-sm text-muted">
            Daily digest
            <input
              type="checkbox"
              checked={profile?.preferences.notification_digest ?? false}
              onChange={(event) => void updatePreferences({ notification_digest: event.target.checked })}
            />
          </label>

          <label className="flex items-center justify-between rounded-2xl bg-white/[0.02] px-4 py-3 text-sm text-muted">
            Release alerts
            <input
              type="checkbox"
              checked={profile?.preferences.notification_releases ?? false}
              onChange={(event) => void updatePreferences({ notification_releases: event.target.checked })}
            />
          </label>
        </div>
      </section>

      <section className="panel-surface px-5 py-5">
        <SectionHeader
          title="Saved Views"
          description="Apply a saved setup to jump back into a workflow without rebuilding filters."
        />
        <div className="mt-4 space-y-3">
          {profile?.saved_views.length ? (
            profile.saved_views.map((view) => (
              <div key={view.id} className="flex flex-wrap items-center justify-between gap-3 rounded-2xl bg-white/[0.02] px-4 py-3">
                <div>
                  <div className="text-sm font-semibold text-ink">{view.name}</div>
                  <div className="mt-1 text-xs text-muted">
                    {(view.feed_mode ?? 'all').replace(/_/g, ' ')} · {(view.sort_mode ?? 'newest').replace(/_/g, ' ')}
                  </div>
                </div>
                <div className="flex gap-2">
                  <button
                    type="button"
                    onClick={() =>
                      setFilters({
                        league: view.league ?? undefined,
                        signal_type: view.signal_type ?? undefined,
                        player: view.player ?? undefined,
                        sort: view.sort_mode,
                        feed: view.feed_mode,
                      })
                    }
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
            ))
          ) : (
            <p className="text-sm text-muted">Save a feed view from the Feed page and it will appear here for quick reuse.</p>
          )}
        </div>
      </section>
    </div>
  );
}
