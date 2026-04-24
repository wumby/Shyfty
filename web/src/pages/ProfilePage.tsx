import { useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';

import { api } from '../services/api';
import { PageIntro } from '../components/PageIntro';
import { SectionHeader } from '../components/SectionHeader';
import { useAuthStore } from '../store/useAuthStore';
import { useSignalStore } from '../store/useSignalStore';
import type { FeedMode, ProfilePreferences, Signal, SortMode } from '../types';

function DashboardIcon({ path }: { path: string }) {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 fill-none stroke-current" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round">
      <path d={path} />
    </svg>
  );
}

function formatFeedMode(value: FeedMode) {
  return value.replace(/_/g, ' ');
}

function formatSortMode(value: SortMode) {
  return value.replace(/_/g, ' ');
}

function buildSavedViewSummary(view: {
  league: string | null;
  signal_type: string | null;
  player: string | null;
  sort_mode: SortMode;
  feed_mode: FeedMode;
}) {
  const parts = [
    view.league ?? 'All leagues',
    view.signal_type ?? 'All signals',
    view.player ? `Player: ${view.player}` : 'All players',
    `Feed: ${formatFeedMode(view.feed_mode)}`,
    `Sort: ${formatSortMode(view.sort_mode)}`,
  ];
  return parts.join(' • ');
}

function buildSignalSummary(signal: Signal) {
  const delta = Math.round(signal.current_value - signal.baseline_value);
  const prefix = delta >= 0 ? '+' : '';
  const metric = signal.metric_label ?? signal.metric_name;
  return `${prefix}${delta} ${metric} ${signal.severity ?? signal.signal_type}`;
}

function buildGameInfo(signal: Signal) {
  const side = signal.home_away === 'away' ? '@' : 'vs';
  return `${signal.team_name} ${side} ${signal.opponent ?? 'Opponent'} • ${signal.league_name}`;
}

function ToggleRow({
  label,
  description,
  checked,
  onToggle,
}: {
  label: string;
  description: string;
  checked: boolean;
  onToggle: () => void;
}) {
  return (
    <button
      type="button"
      role="switch"
      aria-checked={checked}
      onClick={onToggle}
      className="flex w-full items-center justify-between rounded-[22px] border border-border bg-white/[0.03] px-4 py-3 text-left transition hover:border-borderStrong hover:bg-white/[0.05]"
    >
      <div className="pr-4">
        <div className="text-sm font-medium text-ink">{label}</div>
        <div className="mt-1 text-xs text-muted">{description}</div>
      </div>
      <span
        className={`relative inline-flex h-7 w-12 shrink-0 rounded-full border transition ${
          checked ? 'border-accent/60 bg-accentSoft' : 'border-border bg-white/[0.05]'
        }`}
      >
        <span
          className={`absolute top-0.5 h-[22px] w-[22px] rounded-full bg-white shadow-sm transition ${
            checked ? 'left-[22px] bg-[#ffd8bd]' : 'left-0.5'
          }`}
        />
      </span>
    </button>
  );
}

export function ProfilePage() {
  const navigate = useNavigate();
  const currentUser = useAuthStore((state) => state.currentUser);
  const openAuth = useAuthStore((state) => state.openAuth);
  const signOut = useAuthStore((state) => state.signOut);
  const { profile, fetchProfile, updatePreferences, deleteSavedView, setFilters } = useSignalStore();
  const [recentActivity, setRecentActivity] = useState<Signal[]>([]);
  const [activityLoading, setActivityLoading] = useState(false);

  useEffect(() => {
    if (currentUser) void fetchProfile();
  }, [currentUser, fetchProfile]);

  useEffect(() => {
    if (!currentUser || !profile) return;
    const profileData = profile;

    async function loadRecentActivity() {
      setActivityLoading(true);
      try {
        const hasFollows = profileData.follows.players.length > 0 || profileData.follows.teams.length > 0;
        const page = await api.getSignals(
          {
            feed: hasFollows ? 'following' : 'all',
            sort: 'newest',
            league: profileData.preferences.preferred_league ?? undefined,
          },
        );
        setRecentActivity(page.items.slice(0, 5));
      } catch {
        setRecentActivity([]);
      } finally {
        setActivityLoading(false);
      }
    }

    void loadRecentActivity();
  }, [currentUser, profile]);

  const identityLabel = useMemo(() => {
    if (!currentUser?.email) return 'Analyst';
    return currentUser.email.split('@')[0];
  }, [currentUser?.email]);

  const statBadges = useMemo(() => {
    const followingCount = (profile?.follows.players.length ?? 0) + (profile?.follows.teams.length ?? 0);
    return [
      { label: 'Saved Views', value: String(profile?.saved_views.length ?? 0) },
      { label: 'Following', value: String(followingCount) },
      { label: 'Preferred Severity', value: profile?.preferences.preferred_signal_type ?? 'Any' },
    ];
  }, [profile]);

  function openSavedView(view: NonNullable<typeof profile>['saved_views'][number]) {
    setFilters({
      league: view.league ?? undefined,
      signal_type: view.signal_type ?? undefined,
      player: view.player ?? undefined,
      sort: view.sort_mode,
      feed: view.feed_mode,
    });
    navigate('/');
  }

  async function handlePreferenceUpdate(payload: Partial<ProfilePreferences>) {
    await updatePreferences(payload);
  }

  if (!currentUser) {
    return (
      <div className="space-y-6">
        <PageIntro
          eyebrow="Account"
          title="Profile"
          description="Sign in to unlock your Shyfty hub with saved views, activity, and preferences tailored to how you track signals."
        />
        <section className="panel-surface px-6 py-8">
          <SectionHeader
            title="Account Info"
            description="You need an account to save views, follow players or teams, and keep your preferred defaults."
            icon={<DashboardIcon path="M4 12h16M12 4v16" />}
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
    <div className="space-y-6">
      <PageIntro
        eyebrow="User Hub"
        title="Profile"
        description="Your Shyfty home base for identity, saved workflows, and the signal patterns you keep returning to."
      />

      <section className="panel-surface hero-grid relative overflow-hidden px-5 py-5 sm:px-6 sm:py-6">
        <div className="absolute inset-0 bg-[radial-gradient(circle_at_top_right,rgba(249,115,22,0.12),transparent_30%),linear-gradient(135deg,rgba(255,255,255,0.03),transparent_55%)]" />
        <div className="relative grid gap-5 lg:grid-cols-[minmax(0,1.45fr)_minmax(280px,0.9fr)]">
          <div className="flex flex-col gap-5 rounded-[24px] border border-white/10 bg-[#09172a]/70 px-5 py-5">
            <div className="flex flex-col gap-4 sm:flex-row sm:items-center">
              <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-full border border-white/10 bg-white/[0.05] text-lg font-semibold text-[#ffd8bd]">
                {identityLabel.slice(0, 2).toUpperCase()}
              </div>
              <div className="min-w-0">
                <div className="eyebrow text-[#ffd8bd]">Profile Hero</div>
                <h2 className="mt-2 truncate text-3xl font-semibold text-ink">{identityLabel}</h2>
                <p className="mt-1 truncate text-sm text-muted">{currentUser.email}</p>
                <div className="mt-3 inline-flex items-center gap-2 rounded-full border border-border bg-white/[0.04] px-3 py-1.5 text-xs text-muted">
                  <span className="h-2 w-2 rounded-full bg-accent" />
                  Favorite team/player: Coming soon
                </div>
              </div>
            </div>

            <div className="grid gap-3 sm:grid-cols-3">
              {statBadges.map((badge) => (
                <div key={badge.label} className="rounded-[20px] border border-border bg-white/[0.03] px-4 py-3">
                  <div className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted">{badge.label}</div>
                  <div className="mt-2 text-xl font-semibold text-ink">{badge.value}</div>
                </div>
              ))}
            </div>
          </div>

          <div className="rounded-[24px] border border-border bg-white/[0.03] px-5 py-5">
            <div className="eyebrow">Quick Pulse</div>
            <div className="mt-3 text-2xl font-semibold text-ink">
              {profile?.saved_views.length ? 'Your workflows are ready.' : 'Start shaping your board.'}
            </div>
            <p className="mt-2 text-sm leading-6 text-muted">
              {profile?.saved_views.length
                ? 'Open a saved view, jump back into your preferred feed, or tighten defaults from the compact preferences panel below.'
                : 'Save a view from the feed to pin your best setup here, then use it as your fastest way back into Shyfty.'}
            </p>
            <div className="mt-5 flex flex-wrap gap-2">
              <Link to="/" className="pill-button pill-button-active">
                Open feed
              </Link>
              <Link to="/players" className="pill-button">
                Explore players
              </Link>
            </div>
          </div>
        </div>
      </section>

      <section className="panel-surface px-5 py-5">
        <SectionHeader
          title="Saved Views"
          description="Reusable setups that bring you back to the exact feed slices you care about."
          icon={<DashboardIcon path="M4 7.5h16M4 12h10M4 16.5h16" />}
          aside={
            profile?.saved_views.length ? (
              <div className="rounded-full border border-border bg-white/[0.03] px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted">
                {profile.saved_views.length} saved
              </div>
            ) : null
          }
        />
        <div className="mt-5">
          {profile?.saved_views.length ? (
            <div className="grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              {profile.saved_views.map((view) => (
                <article key={view.id} className="rounded-[24px] border border-border bg-white/[0.03] px-4 py-4 transition hover:border-borderStrong hover:bg-white/[0.05]">
                  <div className="flex items-start justify-between gap-3">
                    <div>
                      <div className="text-base font-semibold text-ink">{view.name}</div>
                      <div className="mt-2 text-sm leading-6 text-muted">{buildSavedViewSummary(view)}</div>
                    </div>
                    <div className="rounded-full border border-border bg-[#09172a] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.16em] text-[#ffd8bd]">
                      {view.league ?? 'Mixed'}
                    </div>
                  </div>
                  <div className="mt-5 flex items-center gap-2">
                    <button
                      type="button"
                      onClick={() => openSavedView(view)}
                      className="rounded-full bg-accent px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-white transition hover:brightness-110"
                    >
                      Open
                    </button>
                    <button
                      type="button"
                      onClick={() => void deleteSavedView(view.id)}
                      className="rounded-full border border-border px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted transition hover:text-danger"
                    >
                      Delete
                    </button>
                  </div>
                </article>
              ))}
            </div>
          ) : (
            <div className="rounded-[24px] border border-dashed border-borderStrong bg-[#09172a]/60 px-5 py-6">
              <div className="text-lg font-semibold text-ink">No saved views yet</div>
              <p className="mt-2 max-w-2xl text-sm leading-6 text-muted">
                Save a feed setup once and it becomes your fastest way back to the players, filters, and sorting modes you actually use.
              </p>
              <button
                type="button"
                onClick={() => navigate('/')}
                className="mt-4 rounded-full bg-accent px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-white transition hover:brightness-110"
              >
                Save your first view
              </button>
            </div>
          )}
        </div>
      </section>

      <section className="panel-surface px-5 py-5">
        <SectionHeader
          title="Recent Activity"
          description="A quick look at the latest signal movement connected to your account habits and preferred league."
          icon={<DashboardIcon path="M5 12h3l2.5-4 3 8 2.5-5H19" />}
        />
        <div className="mt-5 space-y-3">
          {activityLoading ? (
            <div className="rounded-[24px] border border-border bg-white/[0.03] px-4 py-5 text-sm text-muted">
              Loading recent activity…
            </div>
          ) : recentActivity.length ? (
            recentActivity.map((signal) => (
              <div key={signal.id} className="flex flex-col gap-3 rounded-[22px] border border-border bg-white/[0.03] px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
                <div className="min-w-0">
                  <div className="text-sm font-semibold text-ink">{signal.player_name}</div>
                  <div className="mt-1 text-sm text-[#ffd8bd]">{buildSignalSummary(signal)}</div>
                  <div className="mt-1 text-xs text-muted">{buildGameInfo(signal)}</div>
                </div>
                <Link
                  to="/"
                  onClick={() => setFilters({ sort: 'newest', feed: profile?.preferences.default_feed_mode ?? 'all' })}
                  className="inline-flex items-center justify-center rounded-full border border-border px-3 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted transition hover:border-borderStrong hover:text-ink"
                >
                  Open feed
                </Link>
              </div>
            ))
          ) : (
            <div className="rounded-[24px] border border-dashed border-borderStrong bg-[#09172a]/60 px-5 py-6">
              <div className="text-lg font-semibold text-ink">No recent activity yet</div>
              <p className="mt-2 text-sm leading-6 text-muted">
                Follow players or teams and browse the feed to start building a more personal activity trail here.
              </p>
            </div>
          )}
        </div>
      </section>

      <section className="panel-surface px-5 py-5">
        <SectionHeader
          title="Preferences"
          description="Compact defaults for how your dashboard and feed should behave."
          icon={<DashboardIcon path="M12 3v3M12 18v3M4.9 4.9l2.1 2.1M17 17l2.1 2.1M3 12h3M18 12h3M4.9 19.1 7 17M17 7l2.1-2.1" />}
        />
        <div className="mt-5 grid gap-5 xl:grid-cols-[minmax(0,1fr)_minmax(320px,0.95fr)]">
          <div className="grid gap-3 sm:grid-cols-2">
            <label className="max-w-sm text-sm text-muted">
              Preferred league
              <select
                value={profile?.preferences.preferred_league ?? ''}
                onChange={(event) => void handlePreferenceUpdate({ preferred_league: event.target.value || null })}
                className="field-shell mt-2 w-full px-3 py-2 text-sm text-ink"
              >
                <option value="">All leagues</option>
                <option value="NBA">NBA</option>
                <option value="NFL">NFL</option>
              </select>
            </label>

            <label className="max-w-sm text-sm text-muted">
              Preferred severity
              <select
                value={profile?.preferences.preferred_signal_type ?? ''}
                onChange={(event) => void handlePreferenceUpdate({ preferred_signal_type: event.target.value || null })}
                className="field-shell mt-2 w-full px-3 py-2 text-sm text-ink"
              >
                <option value="">Any severity</option>
                <option value="OUTLIER">Outlier</option>
                <option value="SWING">Swing</option>
                <option value="SHIFT">Shift</option>
              </select>
            </label>

            <label className="max-w-sm text-sm text-muted">
              Default feed
              <select
                value={profile?.preferences.default_feed_mode ?? 'all'}
                onChange={(event) => void handlePreferenceUpdate({ default_feed_mode: event.target.value as FeedMode })}
                className="field-shell mt-2 w-full px-3 py-2 text-sm text-ink"
              >
                <option value="all">All</option>
                <option value="following">Following</option>
                <option value="for_you">For You</option>
              </select>
            </label>

            <label className="max-w-sm text-sm text-muted">
              Default sort
              <select
                value={profile?.preferences.default_sort_mode ?? 'newest'}
                onChange={(event) => void handlePreferenceUpdate({ default_sort_mode: event.target.value as SortMode })}
                className="field-shell mt-2 w-full px-3 py-2 text-sm text-ink"
              >
                <option value="newest">Newest</option>
                <option value="most_important">Most important</option>
                <option value="biggest_deviation">Biggest deviation</option>
                <option value="most_discussed">Most discussed</option>
              </select>
            </label>
          </div>

          <div className="grid gap-3">
            <ToggleRow
              label="Daily digest"
              description="Get a tighter summary of what changed in your tracked signal universe."
              checked={profile?.preferences.notification_digest ?? false}
              onToggle={() => void handlePreferenceUpdate({ notification_digest: !(profile?.preferences.notification_digest ?? false) })}
            />
            <ToggleRow
              label="Release alerts"
              description="Surface product and feature updates without pulling focus from the feed."
              checked={profile?.preferences.notification_releases ?? false}
              onToggle={() => void handlePreferenceUpdate({ notification_releases: !(profile?.preferences.notification_releases ?? false) })}
            />
          </div>
        </div>
      </section>

      <section className="panel-surface px-5 py-4">
        <SectionHeader
          title="Account Info"
          description="Session controls live here now so the dashboard stays focused on activity."
          icon={<DashboardIcon path="M12 12a4 4 0 1 0 0-8 4 4 0 0 0 0 8Zm-7 9a7 7 0 0 1 14 0" />}
        />
        <div className="mt-4 flex flex-col gap-3 rounded-[22px] border border-border bg-white/[0.03] px-4 py-4 sm:flex-row sm:items-center sm:justify-between">
          <div className="min-w-0">
            <div className="text-sm font-semibold text-ink">{currentUser.email}</div>
            <div className="mt-1 text-xs text-muted">Signed in and synced across your Shyfty workflow.</div>
          </div>
          <button
            type="button"
            onClick={() => void signOut()}
            className="rounded-full border border-border px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.16em] text-muted transition hover:border-borderStrong hover:text-ink"
          >
            Sign Out
          </button>
        </div>
      </section>
    </div>
  );
}
