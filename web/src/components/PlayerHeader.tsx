import type { PlayerDetail } from '../types';
import { useAuthStore } from '../store/useAuthStore';
import { useSignalStore } from '../store/useSignalStore';

export function PlayerHeader({ player }: { player: PlayerDetail }) {
  const currentUser = useAuthStore((s) => s.currentUser);
  const openAuth = useAuthStore((s) => s.openAuth);
  const toggleFollowPlayer = useSignalStore((s) => s.toggleFollowPlayer);
  const profile = useSignalStore((s) => s.profile);

  const isFollowed = profile?.follows.players.includes(player.id) ?? player.is_followed;

  async function handleFollow() {
    if (!currentUser) { openAuth('signin'); return; }
    await toggleFollowPlayer(player.id, isFollowed);
  }

  return (
    <div className="panel-surface hero-grid p-6">
      <div className="eyebrow text-[#ffd8bd]">{player.league_name}</div>
      <div className="mt-3 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-4xl font-semibold text-ink">{player.name}</h2>
          <p className="mt-2 text-sm text-muted">
            {player.team_name} · {player.position}
          </p>
          {isFollowed ? (
            <div className="mt-3 inline-flex items-center gap-2 rounded-full border border-accent/35 bg-accentSoft px-3 py-1.5 text-[11px] font-semibold uppercase tracking-[0.16em] text-[#ffe2cb]">
              <span className="h-2 w-2 rounded-full bg-accent shadow-[0_0_16px_rgba(249,115,22,0.7)]" />
              You&apos;re tracking this player
            </div>
          ) : null}
        </div>
        <div className="flex items-center gap-3">
          <button
            type="button"
            onClick={() => void handleFollow()}
            className={`rounded-full border px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] transition ${
              isFollowed
                ? 'border-accent/40 bg-accentSoft text-accent hover:bg-accent/20'
                : 'border-border bg-white/[0.04] text-muted hover:border-borderStrong hover:text-ink'
            }`}
          >
            {isFollowed ? '✓ Following' : '+ Follow'}
          </button>
          <div className="rounded-[24px] border border-border bg-white/[0.04] px-4 py-3 text-sm text-muted">
            {player.signal_count} active signals
          </div>
        </div>
      </div>
    </div>
  );
}
