import { useEffect, useRef, useState } from 'react';

import { api } from '../services/api';
import type { Comment } from '../types';
import { useAuthStore } from '../store/useAuthStore';

function formatCommentTime(iso: string) {
  const d = new Date(iso);
  const now = Date.now();
  const diffMs = now - d.getTime();
  const diffMins = Math.floor(diffMs / 60000);
  if (diffMins < 1) return 'just now';
  if (diffMins < 60) return `${diffMins}m ago`;
  const diffHrs = Math.floor(diffMins / 60);
  if (diffHrs < 24) return `${diffHrs}h ago`;
  return d.toLocaleDateString('en-US', { month: 'short', day: 'numeric' });
}

function emailHandle(email: string) {
  return email.split('@')[0];
}

interface Props {
  signalId: number;
}

export function CommentsPanel({ signalId }: Props) {
  const [comments, setComments] = useState<Comment[]>([]);
  const [loading, setLoading] = useState(true);
  const [draft, setDraft] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);

  const currentUser = useAuthStore((s) => s.currentUser);
  const openAuth = useAuthStore((s) => s.openAuth);

  useEffect(() => {
    setLoading(true);
    api
      .getComments(signalId)
      .then(setComments)
      .catch(() => setComments([]))
      .finally(() => setLoading(false));
  }, [signalId]);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!currentUser) {
      openAuth('signin');
      return;
    }
    const body = draft.trim();
    if (!body) return;
    setSubmitting(true);
    setError(null);
    try {
      const newComment = await api.postComment(signalId, body);
      setComments((prev) => [...prev, newComment]);
      setDraft('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Failed to post comment');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(commentId: number) {
    try {
      await api.deleteComment(commentId);
      setComments((prev) => prev.filter((c) => c.id !== commentId));
    } catch {
      // ignore
    }
  }

  return (
    <div className="mt-2">
      {loading ? (
        <div className="space-y-2 py-2">
          {[1, 2].map((i) => (
            <div key={i} className="h-10 animate-pulse rounded-lg bg-slate-800/60" />
          ))}
        </div>
      ) : (
        <div className="space-y-2 py-1">
          {comments.length === 0 && (
            <p className="py-1 text-[12px] text-slate-600">No comments yet. Be first.</p>
          )}
          {comments.map((c) => (
            <div key={c.id} className="group flex items-start gap-2.5">
              <div className="flex-1 min-w-0">
                <div className="flex items-baseline gap-2">
                  <span className="text-[11px] font-semibold text-slate-400">{emailHandle(c.user_email)}</span>
                  <span className="text-[10px] text-slate-600">{formatCommentTime(c.created_at)}</span>
                </div>
                <p className="mt-0.5 text-[13px] leading-relaxed text-slate-300">{c.body}</p>
              </div>
              {currentUser?.id === c.user_id && (
                <button
                  type="button"
                  onClick={() => void handleDelete(c.id)}
                  className="mt-0.5 flex-none text-[10px] text-slate-700 opacity-0 transition group-hover:opacity-100 hover:text-red-400"
                >
                  ✕
                </button>
              )}
            </div>
          ))}
        </div>
      )}

      <form onSubmit={(e) => void handleSubmit(e)} className="mt-3 flex gap-2">
        <textarea
          ref={inputRef}
          value={draft}
          onChange={(e) => setDraft(e.target.value)}
          onKeyDown={(e) => {
            if (e.key === 'Enter' && !e.shiftKey) {
              e.preventDefault();
              void handleSubmit(e as unknown as React.FormEvent);
            }
          }}
          placeholder={currentUser ? 'Add a comment…' : 'Sign in to comment'}
          rows={1}
          className="flex-1 resize-none rounded-lg border border-slate-700/60 bg-slate-800/60 px-3 py-2 text-[13px] text-slate-200 placeholder-slate-600 focus:border-slate-600 focus:outline-none"
        />
        <button
          type="submit"
          disabled={submitting || !draft.trim()}
          className="flex-none rounded-lg bg-blue-600/80 px-3 py-2 text-[12px] font-medium text-white transition hover:bg-blue-600 disabled:opacity-40"
        >
          {submitting ? '…' : 'Post'}
        </button>
      </form>
      {error && <p className="mt-1 text-[11px] text-red-400">{error}</p>}
    </div>
  );
}
