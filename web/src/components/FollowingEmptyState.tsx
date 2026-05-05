import { Link } from 'react-router-dom';

import { useAuthStore } from '../store/useAuthStore';
import { useShyftStore } from '../store/useShyftStore';

export function FollowingEmptyState() {
  const currentUser = useAuthStore((state) => state.currentUser);
  const authLoading = useAuthStore((state) => state.authLoading);
  const openAuth = useAuthStore((state) => state.openAuth);
  const profile = useShyftStore((state) => state.profile);

  if (authLoading) return null;

  if (!currentUser) {
    return (
      <div className="rounded-[22px] border border-white/[0.07] bg-white/[0.025] px-4 py-10 text-center">
        <p className="text-sm font-semibold text-ink">Sign in to build your Following feed.</p>
        <button
          type="button"
          onClick={() => openAuth('signin')}
          className="mt-4 inline-flex rounded-full border border-accent/35 bg-accentSoft px-5 py-2 text-xs font-bold text-[#ffd8bd] transition hover:border-accent/60 hover:bg-accent/20"
        >
          Sign in
        </button>
      </div>
    );
  }

  const hasFollows =
    (profile?.follows.players.length ?? 0) > 0 ||
    (profile?.follows.teams.length ?? 0) > 0;

  if (!hasFollows) {
    return (
      <div className="rounded-[22px] border border-white/[0.07] bg-white/[0.025] px-4 py-10 text-center">
        <p className="text-sm font-semibold text-ink">Follow players or teams to build your feed.</p>
        <div className="mt-4 flex justify-center gap-3">
          <Link
            to="/players"
            className="rounded-full border border-border bg-white/[0.03] px-4 py-2 text-xs font-bold text-muted transition hover:border-borderStrong hover:text-ink"
          >
            Browse Players
          </Link>
          <Link
            to="/teams"
            className="rounded-full border border-border bg-white/[0.03] px-4 py-2 text-xs font-bold text-muted transition hover:border-borderStrong hover:text-ink"
          >
            Browse Teams
          </Link>
        </div>
      </div>
    );
  }

  return (
    <div className="rounded-[22px] border border-white/[0.07] bg-white/[0.025] px-4 py-10 text-center text-sm text-muted">
      No shyfts from your follows yet.
    </div>
  );
}
