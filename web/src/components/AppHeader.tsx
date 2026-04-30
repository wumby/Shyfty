import { useEffect, useState } from 'react';
import { NavLink, useLocation } from 'react-router-dom';

import { AuthPanel } from './AuthPanel';
import { SearchModal } from './SearchModal';

const navItems = [
  { to: '/', label: 'Home' },
  { to: '/players', label: 'Players' },
  { to: '/teams', label: 'Teams' },
];

export function AppHeader() {
  const [searchOpen, setSearchOpen] = useState(false);
  const [menuOpen, setMenuOpen] = useState(false);
  const location = useLocation();

  // Close mobile menu on navigation
  useEffect(() => {
    setMenuOpen(false);
  }, [location.pathname]);

  useEffect(() => {
    function handleKey(e: KeyboardEvent) {
      if ((e.metaKey || e.ctrlKey) && e.key === 'k') {
        e.preventDefault();
        setSearchOpen((o) => !o);
      }
      if (e.key === 'Escape') setMenuOpen(false);
    }
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, []);

  return (
    <>
      <header className="sticky top-0 z-50 border-b border-white/[0.07] bg-[#07111f]/88 backdrop-blur-xl">
        <div className="mx-auto flex min-h-[64px] max-w-[1360px] items-center justify-between gap-3 px-4 py-3 sm:px-6">
          <NavLink to="/" className="flex shrink-0 items-center gap-2">
            <span className="accent-dot" />
            <span className="text-sm font-bold uppercase tracking-[0.24em] text-[#fff0e1]">Shyfty</span>
          </NavLink>

          {/* Desktop nav */}
          <nav className="scrollbar-none hidden min-w-0 flex-1 items-center gap-1 overflow-x-auto px-2 sm:flex sm:justify-center">
            {navItems.map((item) => (
              <NavLink
                key={item.to}
                to={item.to}
                end={item.to === '/'}
                className={({ isActive }) =>
                  `whitespace-nowrap rounded-full px-3 py-2 text-sm font-semibold transition ${
                    isActive
                      ? 'bg-accentSoft text-[#ffd8bd]'
                      : 'text-muted hover:bg-white/[0.04] hover:text-ink'
                  }`
                }
              >
                {item.label}
              </NavLink>
            ))}
          </nav>

          <div className="flex shrink-0 items-center gap-2">
            <button
              type="button"
              onClick={() => setSearchOpen(true)}
              className="flex items-center gap-2 rounded-full border border-white/[0.08] bg-white/[0.03] px-3 py-1.5 text-muted transition hover:border-white/[0.14] hover:text-ink"
              aria-label="Search"
            >
              <svg className="h-3.5 w-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                <path strokeLinecap="round" strokeLinejoin="round" d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
              </svg>
              <span className="hidden text-[11px] font-semibold sm:block">Search</span>
              <kbd className="hidden rounded border border-white/10 px-1 py-0.5 text-[9px] sm:block">⌘K</kbd>
            </button>

            <AuthPanel />

            {/* Hamburger — mobile only */}
            <button
              type="button"
              onClick={() => setMenuOpen((o) => !o)}
              className="flex h-8 w-8 items-center justify-center rounded-full border border-white/[0.08] bg-white/[0.03] text-muted transition hover:border-white/[0.14] hover:text-ink sm:hidden"
              aria-label="Menu"
              aria-expanded={menuOpen}
            >
              {menuOpen ? (
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M6 18L18 6M6 6l12 12" />
                </svg>
              ) : (
                <svg className="h-4 w-4" fill="none" viewBox="0 0 24 24" stroke="currentColor" strokeWidth={2}>
                  <path strokeLinecap="round" strokeLinejoin="round" d="M4 6h16M4 12h16M4 18h16" />
                </svg>
              )}
            </button>
          </div>
        </div>

        {/* Mobile nav dropdown */}
        {menuOpen && (
          <div className="border-t border-white/[0.07] px-4 pb-3 pt-2 sm:hidden">
            <nav className="flex flex-col gap-1">
              {navItems.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.to === '/'}
                  className={({ isActive }) =>
                    `rounded-[14px] px-4 py-3 text-sm font-semibold transition ${
                      isActive
                        ? 'bg-accentSoft text-[#ffd8bd]'
                        : 'text-muted hover:bg-white/[0.04] hover:text-ink'
                    }`
                  }
                >
                  {item.label}
                </NavLink>
              ))}
            </nav>
          </div>
        )}
      </header>

      {searchOpen && <SearchModal onClose={() => setSearchOpen(false)} />}
    </>
  );
}
