import { useEffect } from 'react';
import { createPortal } from 'react-dom';

import { CommentsPanel } from './CommentsPanel';

interface Props {
  shyftId: number;
  title: string;
  subtitle?: string;
  onCountChange?: (count: number) => void;
  onClose: () => void;
}

export function ShyftCommentsDrawer({ shyftId, title, subtitle, onCountChange, onClose }: Props) {
  useEffect(() => {
    function handleKey(event: KeyboardEvent) {
      if (event.key === 'Escape') onClose();
    }
    window.addEventListener('keydown', handleKey);
    return () => window.removeEventListener('keydown', handleKey);
  }, [onClose]);

  return createPortal(
    <>
      <div className="fixed inset-0 z-[70] bg-black/45 backdrop-blur-[6px]" onClick={onClose} />
      <div className="fixed bottom-3 right-3 top-3 z-[80] flex w-[calc(100%-1.5rem)] max-w-[520px] flex-col overflow-hidden rounded-[28px] border border-borderStrong bg-[#07111f]/95 shadow-2xl backdrop-blur-2xl">
        <div className="flex items-center justify-between border-b border-border px-5 py-4">
          <div className="min-w-0">
            <div className="eyebrow">Thread</div>
            <div className="truncate text-lg font-semibold text-ink">{title}</div>
            {subtitle ? <div className="truncate text-xs text-muted">{subtitle}</div> : null}
          </div>
          <button type="button" onClick={onClose} className="text-xs text-muted transition hover:text-ink">
            Close ✕
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5 py-5">
          <CommentsPanel shyftId={shyftId} onCountChange={onCountChange} />
        </div>
      </div>
    </>,
    document.body,
  );
}
