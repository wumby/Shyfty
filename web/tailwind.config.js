/** @type {import('tailwindcss').Config} */
export default {
  content: ['./index.html', './src/**/*.{ts,tsx}'],
  theme: {
    extend: {
      colors: {
        bg: 'var(--color-bg)',
        panel: 'var(--color-panel)',
        panelStrong: 'var(--color-panel-strong)',
        border: 'var(--color-border)',
        borderStrong: 'var(--color-border-strong)',
        accent: 'var(--color-accent)',
        accentSoft: 'var(--color-accent-soft)',
        ink: 'var(--color-ink)',
        muted: 'var(--color-muted)',
        success: 'var(--color-success)',
        danger: 'var(--color-danger)',
        warning: 'var(--color-warning)',
      },
    },
  },
  plugins: [],
};
