import { useEffect, useRef, useState } from 'react';

import type { Player } from '../types';

interface Props {
  value: string;
  players: Player[];
  onChange: (value: string) => void;
  placeholder?: string;
}

export function SearchInput({ value, players, onChange, placeholder = 'Search players…' }: Props) {
  const [inputValue, setInputValue] = useState(value);
  const [showSuggestions, setShowSuggestions] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);
  const debounceRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  // Keep local input in sync with external value (e.g. from URL hydration)
  useEffect(() => {
    setInputValue(value);
  }, [value]);

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const next = e.target.value;
    setInputValue(next);
    setShowSuggestions(true);

    if (debounceRef.current) clearTimeout(debounceRef.current);
    debounceRef.current = setTimeout(() => {
      onChange(next);
    }, 300);
  }

  function handleSelect(name: string) {
    setInputValue(name);
    setShowSuggestions(false);
    onChange(name);
  }

  function handleClear() {
    setInputValue('');
    setShowSuggestions(false);
    onChange('');
    inputRef.current?.focus();
  }

  const suggestions =
    inputValue.length >= 2
      ? players
          .filter((p) => p.name.toLowerCase().includes(inputValue.toLowerCase()))
          .slice(0, 6)
      : [];

  return (
    <div className="relative min-w-0 flex-1">
      <div className="flex items-center gap-2 rounded-full border border-border bg-white/[0.04] px-3 py-2 transition focus-within:border-borderStrong focus-within:bg-white/[0.06]">
        <svg className="h-3.5 w-3.5 shrink-0 text-muted/60" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
          <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
        </svg>
        <input
          ref={inputRef}
          type="text"
          value={inputValue}
          onChange={handleChange}
          onFocus={() => inputValue.length >= 2 && setShowSuggestions(true)}
          onBlur={() => setTimeout(() => setShowSuggestions(false), 150)}
          placeholder={placeholder}
          className="min-w-0 flex-1 bg-transparent text-[12px] text-ink placeholder:text-muted/50 focus:outline-none"
        />
        {inputValue && (
          <button
            type="button"
            onClick={handleClear}
            className="shrink-0 text-muted/60 transition hover:text-ink"
          >
            <svg className="h-3 w-3" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2.5}>
              <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {showSuggestions && suggestions.length > 0 && (
        <ul className="absolute left-0 right-0 top-full z-50 mt-1 overflow-hidden rounded-[18px] border border-borderStrong bg-[#07111f]/95 py-1 shadow-2xl backdrop-blur-xl">
          {suggestions.map((player) => (
            <li key={player.id}>
              <button
                type="button"
                onMouseDown={() => handleSelect(player.name)}
                className="flex w-full items-center gap-3 px-4 py-2.5 text-left transition hover:bg-white/[0.05]"
              >
                <span className="text-[13px] font-medium text-ink">{player.name}</span>
                <span className="ml-auto text-[11px] text-muted">{player.team_name}</span>
              </button>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
