import { Component, type ErrorInfo, type ReactNode } from 'react';

interface Props {
  children: ReactNode;
}

interface State {
  error: Error | null;
}

export class ErrorBoundary extends Component<Props, State> {
  state: State = { error: null };

  static getDerivedStateFromError(error: Error): State {
    return { error };
  }

  componentDidCatch(error: Error, info: ErrorInfo) {
    console.error('[ErrorBoundary]', error, info.componentStack);
  }

  render() {
    if (this.state.error) {
      return (
        <div className="flex min-h-screen items-center justify-center bg-[#07111f] px-4">
          <div className="w-full max-w-sm rounded-[24px] border border-border bg-white/[0.03] p-8 text-center">
            <div className="eyebrow mb-2">Something went wrong</div>
            <p className="mb-6 text-sm text-muted">Try reloading the page. If it keeps happening, the issue has been logged.</p>
            <button
              type="button"
              onClick={() => window.location.reload()}
              className="rounded-full border border-border bg-white/[0.04] px-5 py-2 text-sm font-semibold text-ink transition hover:border-borderStrong"
            >
              Reload
            </button>
          </div>
        </div>
      );
    }
    return this.props.children;
  }
}
