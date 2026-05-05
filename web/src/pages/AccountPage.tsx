import { useEffect, useMemo, useState } from 'react';
import { useNavigate } from 'react-router-dom';

import { api } from '../services/api';
import { useAuthStore } from '../store/useAuthStore';
import { useShyftStore } from '../store/useShyftStore';

type ModalMode = 'editProfile' | 'changePassword' | null;

function formatMemberSince(iso: string) {
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  return date.toLocaleDateString('en-US', { month: 'short', day: 'numeric', year: 'numeric' });
}

function Row({ label, onClick }: { label: string; onClick: () => void }) {
  return (
    <button
      type="button"
      onClick={onClick}
      className="flex w-full items-center justify-between rounded-[12px] px-1 py-2 text-left transition hover:bg-white/[0.03]"
    >
      <span className="text-sm text-ink">{label}</span>
      <span className="text-sm text-muted">›</span>
    </button>
  );
}

export function AccountPage() {
  const navigate = useNavigate();
  const currentUser = useAuthStore((state) => state.currentUser);
  const openAuth = useAuthStore((state) => state.openAuth);
  const signOut = useAuthStore((state) => state.signOut);
  const refreshSession = useAuthStore((state) => state.refreshSession);
  const {
    profile,
    players,
    teams,
    fetchProfile,
    fetchPlayers,
    fetchTeams,
    toggleFollowPlayer,
    toggleFollowTeam,
  } = useShyftStore();
  const [modalMode, setModalMode] = useState<ModalMode>(null);
  const [globalMessage, setGlobalMessage] = useState<string | null>(null);

  useEffect(() => {
    if (!currentUser) return;
    void fetchProfile();
    if (!players.length) void fetchPlayers();
    if (!teams.length) void fetchTeams();
  }, [currentUser, fetchProfile, fetchPlayers, fetchTeams, players.length, teams.length]);

  if (!currentUser) {
    return (
      <div className="panel-surface mx-auto max-w-[760px] px-6 py-8 text-center">
        <p className="text-sm text-muted">Sign in to manage follows and account settings.</p>
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
  const fallbackName = useMemo(() => currentUser.email.split('@')[0], [currentUser.email]);
  const resolvedName = profile?.display_name || currentUser.display_name || fallbackName;
  const followedTotal = followedPlayers.length + followedTeams.length;

  return (
    <>
      <div className="mx-auto max-w-[760px] space-y-4">
        <section className="panel-surface px-5 py-3">
          <div className="flex items-center justify-between gap-4">
            <div className="min-w-0">
              <div className="truncate text-lg font-semibold text-ink">{resolvedName}</div>
              <div className="mt-0.5 truncate text-xs text-muted">{currentUser.email}</div>
              <div className="mt-0.5 truncate text-[11px] text-muted/80">Member since {formatMemberSince(currentUser.created_at)}</div>
            </div>
            <button
              type="button"
              onClick={() => void signOut()}
              className="shrink-0 rounded-full border border-border px-3 py-1.5 text-[11px] font-semibold text-muted transition hover:border-danger/50 hover:text-danger"
            >
              Sign Out
            </button>
          </div>
        </section>

        <section className="panel-surface px-5 py-4">
          <div className="mb-2 text-[10px] font-semibold uppercase tracking-[0.18em] text-muted">Account</div>
          <div className="divide-y divide-border">
            <Row label="Edit Display Name" onClick={() => setModalMode('editProfile')} />
            <Row label="Change Password" onClick={() => setModalMode('changePassword')} />
          </div>
        </section>

        <section className="panel-surface px-5 py-4">
          <div className="mb-3 flex items-center justify-between">
            <h2 className="text-[10px] font-semibold uppercase tracking-[0.18em] text-muted">Following</h2>
            <span className="text-[11px] text-muted">{followedTotal} following</span>
          </div>

          {hasFollows ? (
            <div className="space-y-1.5">
              {followedPlayers.map((player) => (
                <div key={player.id} className="flex items-center justify-between gap-4 rounded-[12px] border border-border bg-white/[0.02] px-3 py-2">
                  <div className="min-w-0">
                    <button type="button" onClick={() => navigate(`/players/${player.id}`)} className="truncate text-sm font-semibold text-ink hover:text-accent">
                      {player.name}
                    </button>
                    <div className="mt-0.5 text-[11px] text-muted">{player.team_name} · {player.position}</div>
                  </div>
                  <button type="button" onClick={() => void toggleFollowPlayer(player.id, true)} className="shrink-0 text-[11px] font-semibold text-muted transition hover:text-danger">
                    Unfollow
                  </button>
                </div>
              ))}
              {followedTeams.map((team) => (
                <div key={team.id} className="flex items-center justify-between gap-4 rounded-[12px] border border-border bg-white/[0.02] px-3 py-2">
                  <div className="min-w-0">
                    <span className="truncate text-sm font-semibold text-ink">{team.name}</span>
                    <div className="mt-0.5 text-[11px] text-muted">{team.league_name}</div>
                  </div>
                  <button type="button" onClick={() => void toggleFollowTeam(team.id, true)} className="shrink-0 text-[11px] font-semibold text-muted transition hover:text-danger">
                    Unfollow
                  </button>
                </div>
              ))}
            </div>
          ) : (
            <div className="space-y-3">
              <p className="text-sm text-muted">You’re not following anyone yet.</p>
              <button
                type="button"
                onClick={() => navigate('/players')}
                className="rounded-full border border-border px-4 py-2 text-xs font-semibold text-ink transition hover:border-borderStrong"
              >
                Browse Players
              </button>
            </div>
          )}
        </section>

        {globalMessage ? (
          <div className="px-1 text-xs text-muted">{globalMessage}</div>
        ) : null}
      </div>

      {modalMode === 'editProfile' ? (
        <EditProfileModal
          initialDisplayName={profile?.display_name ?? currentUser.display_name ?? ''}
          fallbackName={fallbackName}
          onClose={() => setModalMode(null)}
          onSaved={async (msg) => {
            await Promise.all([refreshSession(), fetchProfile()]);
            setGlobalMessage(msg);
            setModalMode(null);
          }}
        />
      ) : null}

      {modalMode === 'changePassword' ? (
        <ChangePasswordModal
          onClose={() => setModalMode(null)}
          onSuccess={async (msg) => {
            setGlobalMessage(msg);
            setModalMode(null);
            await signOut();
            openAuth('signin');
          }}
        />
      ) : null}
    </>
  );
}

function EditProfileModal({
  initialDisplayName,
  fallbackName,
  onClose,
  onSaved,
}: {
  initialDisplayName: string;
  fallbackName: string;
  onClose: () => void;
  onSaved: (message: string) => Promise<void>;
}) {
  const [name, setName] = useState(initialDisplayName);
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setIsSaving(true);
    setError(null);
    try {
      await api.updateProfile({ display_name: name.trim() || null });
      await onSaved('Profile updated.');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to save profile');
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[90] bg-black/60 backdrop-blur-sm">
      <div className="panel-surface mx-auto mt-20 w-[calc(100%-2rem)] max-w-[520px] p-5">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-ink">Edit Profile</h3>
          <button type="button" onClick={onClose} className="text-xs text-muted hover:text-ink">Close</button>
        </div>
        <label className="block">
          <div className="mb-1 text-[11px] text-muted">Display Name</div>
          <input
            value={name}
            onChange={(event) => setName(event.target.value)}
            maxLength={80}
            className="field-shell w-full rounded-[12px] px-3 py-2 text-sm"
            placeholder={fallbackName}
          />
        </label>
        {error ? <div className="mt-2 text-xs text-danger">{error}</div> : null}
        <div className="mt-4 flex justify-end">
          <button
            type="button"
            onClick={() => void save()}
            disabled={isSaving}
            className="rounded-full bg-accent px-4 py-2 text-xs font-semibold text-white disabled:opacity-60"
          >
            {isSaving ? 'Saving...' : 'Save'}
          </button>
        </div>
      </div>
    </div>
  );
}

function ChangePasswordModal({
  onClose,
  onSuccess,
}: {
  onClose: () => void;
  onSuccess: (message: string) => Promise<void>;
}) {
  const [currentPassword, setCurrentPassword] = useState('');
  const [newPassword, setNewPassword] = useState('');
  const [confirmPassword, setConfirmPassword] = useState('');
  const [isSaving, setIsSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function save() {
    setError(null);
    const current = currentPassword.trim();
    const next = newPassword.trim();
    const confirm = confirmPassword.trim();

    if (!current || !next || !confirm) {
      setError('Please complete all fields.');
      return;
    }
    if (next !== confirm) {
      setError('New password and confirmation do not match.');
      return;
    }
    if (next.length < 8 || !/[A-Za-z]/.test(next) || !/[0-9]/.test(next)) {
      setError('Use at least 8 characters with letters and numbers.');
      return;
    }

    setIsSaving(true);
    try {
      const result = await api.changePassword({
        current_password: current,
        new_password: next,
        confirm_new_password: confirm,
      });
      await onSuccess(result.message);
    } catch (err) {
      const message = err instanceof Error ? err.message : 'Failed to change password';
      if (message.includes('429')) {
        setError('Too many attempts. Try again shortly.');
      } else {
        setError(message);
      }
    } finally {
      setIsSaving(false);
    }
  }

  return (
    <div className="fixed inset-0 z-[90] bg-black/60 backdrop-blur-sm">
      <div className="panel-surface mx-auto mt-20 w-[calc(100%-2rem)] max-w-[520px] p-5">
        <div className="mb-4 flex items-center justify-between">
          <h3 className="text-sm font-semibold text-ink">Change Password</h3>
          <button type="button" onClick={onClose} className="text-xs text-muted hover:text-ink">Close</button>
        </div>
        <div className="space-y-3">
          <input
            type="password"
            value={currentPassword}
            onChange={(event) => setCurrentPassword(event.target.value)}
            className="field-shell w-full rounded-[12px] px-3 py-2 text-sm"
            placeholder="Current password"
          />
          <input
            type="password"
            value={newPassword}
            onChange={(event) => setNewPassword(event.target.value)}
            className="field-shell w-full rounded-[12px] px-3 py-2 text-sm"
            placeholder="New password"
          />
          <input
            type="password"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            className="field-shell w-full rounded-[12px] px-3 py-2 text-sm"
            placeholder="Confirm password"
          />
        </div>
        {error ? <div className="mt-2 text-xs text-danger">{error}</div> : null}
        <div className="mt-4 flex justify-end">
          <button
            type="button"
            onClick={() => void save()}
            disabled={isSaving}
            className="rounded-full bg-accent px-4 py-2 text-xs font-semibold text-white disabled:opacity-60"
          >
            {isSaving ? 'Updating...' : 'Update Password'}
          </button>
        </div>
      </div>
    </div>
  );
}
