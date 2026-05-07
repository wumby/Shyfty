import { useEffect } from 'react';
import { Link, Outlet } from 'react-router-dom';

import { AppHeader } from './AppHeader';
import { useAuthStore } from '../store/useAuthStore';

export function AppShell() {
  const refreshSession = useAuthStore((state) => state.refreshSession);

  useEffect(() => {
    void refreshSession();
  }, [refreshSession]);

  return (
    <div className="flex min-h-screen flex-col">
      <AppHeader />
      <div className="flex-1 px-4 py-6 sm:px-6 lg:py-8">
        <main className="relative z-0 min-w-0">
          <Outlet />
        </main>
      </div>
      <footer className="border-t border-border px-6 py-4">
        <div className="flex flex-wrap items-center justify-center gap-x-5 gap-y-1">
          <span className="text-[11px] text-muted/50">© {new Date().getFullYear()} Shyfty</span>
          <Link to="/terms" className="text-[11px] text-muted/50 transition hover:text-muted">Terms</Link>
          <Link to="/privacy" className="text-[11px] text-muted/50 transition hover:text-muted">Privacy</Link>
        </div>
      </footer>
    </div>
  );
}
