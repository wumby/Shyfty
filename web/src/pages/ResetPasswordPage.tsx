import { useState } from 'react';
import { useNavigate, useSearchParams } from 'react-router-dom';

import { api } from '../services/api';

export function ResetPasswordPage() {
  const [searchParams] = useSearchParams();
  const navigate = useNavigate();
  const token = searchParams.get('token') ?? '';

  const [password, setPassword] = useState('');
  const [confirm, setConfirm] = useState('');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState('');
  const [success, setSuccess] = useState(false);

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (password !== confirm) {
      setError('Passwords do not match.');
      return;
    }
    setLoading(true);
    setError('');
    try {
      await api.resetPassword(token, password, confirm);
      setSuccess(true);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Something went wrong. The link may have expired.');
    } finally {
      setLoading(false);
    }
  }

  if (!token) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-[#07111f] px-4">
        <div className="w-full max-w-sm rounded-[24px] border border-border bg-white/[0.03] p-8 text-center">
          <p className="text-sm text-danger">Invalid reset link.</p>
        </div>
      </div>
    );
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-[#07111f] px-4">
      <div className="w-full max-w-sm rounded-[24px] border border-border bg-white/[0.03] p-8">
        <div className="mb-6">
          <div className="eyebrow mb-1">Shyfty</div>
          <h1 className="text-2xl font-semibold text-ink">Set new password</h1>
        </div>

        {success ? (
          <div className="space-y-4">
            <p className="text-sm leading-relaxed text-[#d9e3f1]">Password updated. You can now sign in with your new password.</p>
            <button
              type="button"
              onClick={() => navigate('/')}
              className="w-full rounded-[18px] bg-accent px-3 py-2.5 text-sm font-semibold text-[#1f1308] transition hover:brightness-110"
            >
              Go to Shyfty
            </button>
          </div>
        ) : (
          <form className="space-y-3" onSubmit={(event) => void handleSubmit(event)}>
            <input
              type="password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              placeholder="New password"
              minLength={8}
              required
              className="field-shell w-full px-3 py-2.5 text-sm placeholder:text-muted/70"
            />
            <input
              type="password"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              placeholder="Confirm password"
              minLength={8}
              required
              className="field-shell w-full px-3 py-2.5 text-sm placeholder:text-muted/70"
            />
            {error ? <p className="text-xs text-danger">{error}</p> : null}
            <button
              type="submit"
              disabled={loading || !password || !confirm}
              className="w-full rounded-[18px] bg-accent px-3 py-2.5 text-sm font-semibold text-[#1f1308] transition hover:brightness-110 disabled:opacity-60"
            >
              {loading ? 'Saving...' : 'Set Password'}
            </button>
          </form>
        )}
      </div>
    </div>
  );
}
