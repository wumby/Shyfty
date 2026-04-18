import { NavLink } from 'react-router-dom';

const navItems = [
  { to: '/', label: 'Signals' },
  { to: '/players', label: 'Players' },
  { to: '/teams', label: 'Teams' },
  { to: '/profile', label: 'Profile' },
];

export function SideNav() {
  return (
    <div className="panel-strong sticky top-0 p-3">
      <div className="eyebrow mb-3 text-[#ffd8bd]">Navigate</div>
      <nav className="flex flex-col gap-1.5">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              `rounded-[20px] border px-3.5 py-2.5 text-sm font-semibold transition ${
                isActive
                  ? 'border-accent/25 bg-accentSoft text-[#ffd8bd]'
                  : 'border-transparent bg-white/[0.02] text-muted hover:border-border hover:bg-white/[0.04] hover:text-ink'
              }`
            }
          >
            {item.label}
          </NavLink>
        ))}
      </nav>
    </div>
  );
}
