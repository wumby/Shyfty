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

function commentAuthorName(comment: Comment) {
  return (comment.user_display_name && comment.user_display_name.trim()) || emailHandle(comment.user_email);
}

interface Props {
  shyftId: number;
  initialComments?: Comment[];
  onCountChange?: (count: number) => void;
}

export function CommentsPanel({ shyftId, initialComments, onCountChange }: Props) {
  const [comments, setComments] = useState<Comment[]>(initialComments ?? []);
  const [loading, setLoading] = useState(!initialComments);
  const [draft, setDraft] = useState('');
  const [submitting, setSubmitting] = useState(false);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editDraft, setEditDraft] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [reportingId, setReportingId] = useState<number | null>(null);
  const inputRef = useRef<HTMLTextAreaElement>(null);
  const onCountChangeRef = useRef(onCountChange);

  const currentUser = useAuthStore((s) => s.currentUser);
  const openAuth = useAuthStore((s) => s.openAuth);

  useEffect(() => {
    onCountChangeRef.current = onCountChange;
  }, [onCountChange]);

  useEffect(() => {
    if (initialComments) return;
    setLoading(true);
    api
      .getComments(shyftId)
      .then((rows) => {
        setComments(rows);
        onCountChangeRef.current?.(rows.length);
      })
      .catch(() => setComments([]))
      .finally(() => setLoading(false));
  }, [initialComments, shyftId]);

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
    const tempId = -Date.now();
    const optimisticComment: Comment = {
      id: tempId,
      shyft_id: shyftId,
      user_id: currentUser.id,
      user_email: currentUser.email,
      user_display_name: currentUser.display_name ?? currentUser.email.split('@')[0],
      body,
      created_at: new Date().toISOString(),
      updated_at: new Date().toISOString(),
      is_edited: false,
      can_edit: true,
      can_delete: true,
      can_report: false,
    };
    setComments((prev) => {
      const next = [...prev, optimisticComment];
      onCountChangeRef.current?.(next.length);
      return next;
    });
    setDraft('');
    try {
      const newComment = await api.postComment(shyftId, body);
      setComments((prev) => {
        const next = prev.map((comment) => (comment.id === tempId ? newComment : comment));
        onCountChangeRef.current?.(next.length);
        return next;
      });
    } catch (err) {
      setComments((prev) => {
        const next = prev.filter((comment) => comment.id !== tempId);
        onCountChangeRef.current?.(next.length);
        return next;
      });
      setDraft(body);
      setError(err instanceof Error ? err.message : 'Failed to post comment');
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(commentId: number) {
    const previous = comments;
    setComments((prev) => {
      const next = prev.filter((c) => c.id !== commentId);
      onCountChangeRef.current?.(next.length);
      return next;
    });
    try {
      await api.deleteComment(commentId);
    } catch (err) {
      setComments(previous);
      onCountChangeRef.current?.(previous.length);
      setError(err instanceof Error ? err.message : 'Delete failed');
    }
  }

  async function handleEdit(commentId: number) {
    const body = editDraft.trim();
    if (!body) return;
    try {
      const updated = await api.updateComment(commentId, body);
      setComments((prev) => prev.map((comment) => (comment.id === commentId ? updated : comment)));
      setEditingId(null);
      setEditDraft('');
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Edit failed');
    }
  }

  async function handleReport(commentId: number) {
    try {
      await api.reportComment(commentId, 'abuse');
      setReportingId(commentId);
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Report failed');
    }
  }

  return (
    <div className="mt-2">
      {/* Input first — makes first interaction feel immediate */}
      <form onSubmit={(e) => void handleSubmit(e)} className="mb-3 flex gap-2">
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
          placeholder={currentUser ? 'Add a read…' : 'Sign in to comment'}
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

      {loading ? (
        <div className="space-y-2 py-2">
          {[1, 2].map((i) => (
            <div key={i} className="h-10 animate-pulse rounded-lg bg-slate-800/60" />
          ))}
        </div>
      ) : (
        <div className="space-y-3 py-1">
          {comments.length === 0 && (
            <p className="text-[12px] italic text-muted/50">
              Set the tone on this shyft. Be the first read everyone else reacts to.
            </p>
          )}
          {comments.map((c) => (
            <div key={c.id} className="group rounded-2xl border border-border bg-white/[0.02] px-3 py-3">
              <div className="flex items-start justify-between gap-3">
                <div className="min-w-0 flex-1">
                  <div className="flex flex-wrap items-center gap-2">
                    <span className="text-[11px] font-semibold text-[#d9e3f1]">{commentAuthorName(c)}</span>
                    <span className="text-[10px] text-muted">{formatCommentTime(c.created_at)}</span>
                    {c.is_edited ? <span className="text-[10px] uppercase tracking-[0.14em] text-muted/70">edited</span> : null}
                  </div>
                  {editingId === c.id ? (
                    <div className="mt-2 flex gap-2">
                      <textarea
                        value={editDraft}
                        onChange={(event) => setEditDraft(event.target.value)}
                        rows={2}
                        className="flex-1 resize-none rounded-lg border border-slate-700/60 bg-slate-800/60 px-3 py-2 text-[13px] text-slate-200 focus:border-slate-600 focus:outline-none"
                      />
                      <div className="flex flex-col gap-2">
                        <button
                          type="button"
                          onClick={() => void handleEdit(c.id)}
                          className="rounded-lg bg-blue-600/80 px-3 py-2 text-[11px] font-medium text-white"
                        >
                          Save
                        </button>
                        <button
                          type="button"
                          onClick={() => { setEditingId(null); setEditDraft(''); }}
                          className="rounded-lg border border-border px-3 py-2 text-[11px] text-muted"
                        >
                          Cancel
                        </button>
                      </div>
                    </div>
                  ) : (
                    <p className="mt-1 text-[13px] leading-relaxed text-slate-300">{c.body}</p>
                  )}
                </div>
                {(c.can_edit || c.can_delete || c.can_report) && editingId !== c.id ? (
                  <div className="flex shrink-0 items-center gap-0.5 opacity-0 transition-opacity group-hover:opacity-100">
                    {c.can_edit ? (
                      <button
                        type="button"
                        onClick={() => { setEditingId(c.id); setEditDraft(c.body); }}
                        className="rounded-md p-1.5 text-muted transition hover:bg-white/[0.07] hover:text-ink"
                        aria-label="Edit"
                      >
                        <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                          <path d="M11 2.5a1.5 1.5 0 0 1 2.5 1.5L5.5 12.5 3 13l.5-2.5L11 2.5Z" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                      </button>
                    ) : null}
                    {c.can_delete ? (
                      <button
                        type="button"
                        onClick={() => void handleDelete(c.id)}
                        className="rounded-md p-1.5 text-muted transition hover:bg-red-500/10 hover:text-red-400"
                        aria-label="Delete"
                      >
                        <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                          <path d="M2 4h12M5 4V2h6v2M4 4l.75 9.5A.75.75 0 0 0 5.5 14h5a.75.75 0 0 0 .75-.5L12 4" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                      </button>
                    ) : null}
                    {c.can_report ? (
                      <button
                        type="button"
                        onClick={() => void handleReport(c.id)}
                        disabled={reportingId === c.id}
                        className="rounded-md p-1.5 text-muted transition hover:bg-amber-500/10 hover:text-amber-400 disabled:opacity-40"
                        aria-label={reportingId === c.id ? 'Reported' : 'Report'}
                      >
                        <svg width="13" height="13" viewBox="0 0 16 16" fill="none" aria-hidden="true">
                          <path d="M3 2v12M3 2h8.5L9 6.5l2.5 4.5H3" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" strokeLinejoin="round"/>
                        </svg>
                      </button>
                    ) : null}
                  </div>
                ) : null}
              </div>
            </div>
          ))}
        </div>
      )}

      {error && <p className="mt-1 text-[11px] text-red-400">{error}</p>}
    </div>
  );
}
