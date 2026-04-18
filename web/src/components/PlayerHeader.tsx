import type { PlayerDetail } from '../types';

export function PlayerHeader({ player }: { player: PlayerDetail }) {
  return (
    <div className="panel-surface hero-grid p-6">
      <div className="eyebrow text-[#ffd8bd]">{player.league_name}</div>
      <div className="mt-3 flex flex-col gap-4 sm:flex-row sm:items-end sm:justify-between">
        <div>
          <h2 className="text-4xl font-semibold text-ink">{player.name}</h2>
          <p className="mt-2 text-sm text-muted">
            {player.team_name} · {player.position}
          </p>
        </div>
        <div className="rounded-[24px] border border-border bg-white/[0.04] px-4 py-3 text-sm text-muted">
          {player.signal_count} active feed events
        </div>
      </div>
    </div>
  );
}
