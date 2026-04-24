import { useEffect, useRef, useState } from 'react';
import { createPortal } from 'react-dom';
import { useNavigate } from 'react-router-dom';

import { useSignalStore } from '../store/useSignalStore';

interface SearchResult {
  id: number;
  label: string;
  sub: string;
  type: 'player' | 'team';
  to: string;
}

interface SearchModalProps {
  onClose: () => void;
}

function SearchModalContent({ onClose }: SearchModalProps) {
  const [query, setQuery] = useState('');
  const [cursor, setCursor] = useState(0);
  const inputRef = useRef<HTMLInputElement>(null);
  const navigate = useNavigate();
  const { players, teams, fetchPlayers, fetchTeams } = useSignalStore();

  useEffect(() => {
    inputRef.current?.focus();
    if (!players.length) void fetchPlayers();
    if (!teams.length) void fetchTeams();
  }, [fetchPlayers, fetchTeams, players.length, teams.length]);

  const q = query.trim().toLowerCase();
  const results: SearchResult[] = q.length < 2 ? [] : [
    ...players
      .filter((p) => p.name.toLowerCase().includes(q) || p.team_name.toLowerCase().includes(q))
      .slice(0, 5)
      .map((p) => ({ id: p.id, label: p.name, sub: `${p.team_name} · ${p.position}`, type: 'player' as const, to: `/players/${p.id}` })),
    ...teams
      .filter((t) => t.name.toLowerCase().includes(q))
      .slice(0, 3)
      .map((t) => ({ id: t.id, label: t.name, sub: t.league_name, type: 'team' as const, to: `/teams/${t.id}` })),
  ];

  function handleSelect(result: SearchResult) {
    navigate(result.to);
    onClose();
  }

  function handleKeyDown(e: React.KeyboardEvent) {
    if (e.key === 'Escape') { onClose(); return; }
    if (e.key === 'ArrowDown') { setCursor((c) => Math.min(c + 1, results.length - 1)); e.preventDefault(); return; }
    if (e.key === 'ArrowUp') { setCursor((c) => Math.max(c - 1, 0)); e.preventDefault(); return; }
    if (e.key === 'Enter' && results[cursor]) handleSelect(results[cursor]);
  }

  useEffect(() => { setCursor(0); }, [query]);

  return (
    <>
      <div className="fixed inset-0 z-[60] bg-black/60 backdrop-blur-sm" onClick={onClose} />
      <div className="fixed left-1/2 top-[12vh] z-[61] w-full max-w-lg -translate-x-1/2 px-4">
        <div className="overflow-hidden rounded-[24px] border border-white/[0.12] bg-[#07111f] shadow-2xl">
          <div className="flex items-center gap-3 border-b border-white/[0.07] px-4 py-3.5">
            <svg className="h-4 w-4 shrink-0 text-muted" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
            </svg>
            <input
              ref={inputRef}
              type="text"
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="Search players and teams…"
              className="min-w-0 flex-1 bg-transparent text-sm text-ink placeholder:text-muted/50 focus:outline-none"
            />
            <kbd className="hidden rounded border border-white/10 px-1.5 py-0.5 text-[10px] text-muted sm:block">esc</kbd>
          </div>

          {q.length >= 2 ? (
            results.length > 0 ? (
              <ul className="max-h-[52vh] overflow-y-auto py-2">
                {results.map((result, i) => (
                  <li key={`${result.type}-${result.id}`}>
                    <button
                      type="button"
                      onMouseDown={() => handleSelect(result)}
                      onMouseEnter={() => setCursor(i)}
                      className={`flex w-full items-center gap-3 px-4 py-2.5 text-left transition ${cursor === i ? 'bg-white/[0.06]' : 'hover:bg-white/[0.04]'}`}
                    >
                      <span className={`shrink-0 rounded-full px-2 py-0.5 text-[9px] font-bold uppercase tracking-[0.14em] ${result.type === 'player' ? 'bg-accent/15 text-accent' : 'bg-sky-400/15 text-sky-300'}`}>
                        {result.type}
                      </span>
                      <span className="min-w-0 flex-1">
                        <span className="block truncate text-sm font-semibold text-ink">{result.label}</span>
                        <span className="block text-xs text-muted">{result.sub}</span>
                      </span>
                      <svg className="h-3 w-3 shrink-0 text-muted/40" fill="none" viewBox="0 0 12 12" stroke="currentColor" strokeWidth={1.5}>
                        <path strokeLinecap="round" strokeLinejoin="round" d="M4.5 2.5L8 6L4.5 9.5" />
                      </svg>
                    </button>
                  </li>
                ))}
              </ul>
            ) : (
              <div className="px-4 py-8 text-center text-sm text-muted">No results for &ldquo;{query}&rdquo;</div>
            )
          ) : (
            <div className="px-4 py-6 text-center text-sm text-muted/50">Type to search players and teams</div>
          )}
        </div>
      </div>
    </>
  );
}

export function SearchModal({ onClose }: SearchModalProps) {
  return createPortal(<SearchModalContent onClose={onClose} />, document.body);
}
