import { useState } from 'react';

import { useAuthStore } from '../store/useAuthStore';

export function AuthPanel() {
  const {
    currentUser,
    authLoading,
    authPanelOpen,
    authMode,
    authError,
    signIn,
    signUp,
    signOut,
    openAuth,
    closeAuth,
  } = useAuthStore();
  const [email, setEmail] = useState('');
  const [password, setPassword] = useState('');

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (authMode === 'signin') {
      await signIn(email, password);
    } else {
      await signUp(email, password);
    }
    setPassword('');
  }

  if (currentUser) {
    return (
      <div className="flex flex-wrap items-center justify-end gap-2">
        <div className="rounded-full border border-border bg-white/[0.03] px-3 py-2 text-xs text-muted">
          {currentUser.email}
        </div>
        <button
          type="button"
          onClick={() => void signOut()}
          className="rounded-full border border-border bg-white/[0.03] px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted transition hover:border-borderStrong hover:bg-white/[0.05] hover:text-ink"
        >
          Sign Out
        </button>
      </div>
    );
  }

  return (
    <div className="relative">
      <div className="flex flex-wrap items-center justify-end gap-2">
        <button
          type="button"
          onClick={() => openAuth('signin')}
          className="rounded-full border border-border bg-white/[0.03] px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-muted transition hover:border-borderStrong hover:bg-white/[0.05] hover:text-ink"
        >
          Sign In
        </button>
        <button
          type="button"
          onClick={() => openAuth('signup')}
          className="rounded-full border border-accent/35 bg-accent px-4 py-2 text-[11px] font-semibold uppercase tracking-[0.18em] text-[#1f1308] transition hover:brightness-110"
        >
          Create Account
        </button>
      </div>
      {authPanelOpen ? (
        <div className="panel-strong absolute right-0 top-[calc(100%+0.75rem)] z-30 w-[300px] p-4">
          <div className="mb-3 flex items-center justify-between gap-3">
            <div className="eyebrow text-[#ffd8bd]">
              {authMode === 'signin' ? 'Sign In' : 'Create Account'}
            </div>
            <button type="button" onClick={closeAuth} className="rounded-full border border-border bg-white/[0.03] px-2.5 py-1 text-[10px] font-semibold uppercase tracking-[0.14em] text-muted transition hover:border-borderStrong hover:text-ink">
              Close
            </button>
          </div>
          <form className="space-y-2.5" onSubmit={(event) => void handleSubmit(event)}>
            <input
              type="email"
              value={email}
              onChange={(event) => setEmail(event.target.value)}
              placeholder="email"
              className="field-shell w-full px-3 py-2.5 text-sm placeholder:text-muted/70"
            />
            <input
              type="password"
              value={password}
              onChange={(event) => setPassword(event.target.value)}
              placeholder="password"
              className="field-shell w-full px-3 py-2.5 text-sm placeholder:text-muted/70"
            />
            {authError ? <div className="text-xs text-danger">{authError}</div> : null}
            <button
              type="submit"
              disabled={authLoading}
              className="w-full rounded-[18px] bg-accent px-3 py-2.5 text-sm font-semibold text-[#1f1308] transition hover:brightness-110 disabled:opacity-60"
            >
              {authLoading ? 'Working...' : authMode === 'signin' ? 'Sign In' : 'Create Account'}
            </button>
          </form>
        </div>
      ) : null}
    </div>
  );
}
