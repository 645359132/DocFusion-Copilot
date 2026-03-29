import { NavLink } from 'react-router-dom';

const navItems = [
  { to: '/upload', label: '上传' },
  { to: '/documents', label: '文档' },
  { to: '/facts', label: '复核' },
  { to: '/agent', label: '回填' },
  { to: '/benchmarks', label: '评测' },
];

export default function MobileNavBar() {
  return (
    <nav className="glass-panel fixed inset-x-4 bottom-4 z-30 rounded-[22px] border border-white/70 px-3 py-3 shadow-card lg:hidden">
      <div className="grid grid-cols-5 gap-2">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              [
                'rounded-2xl px-3 py-3 text-center text-sm font-semibold transition',
                isActive ? 'bg-ink text-white' : 'bg-white/70 text-slate-600 hover:bg-white',
              ].join(' ')
            }
          >
            {item.label}
          </NavLink>
        ))}
      </div>
    </nav>
  );
}