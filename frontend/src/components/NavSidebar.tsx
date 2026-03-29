import { NavLink } from 'react-router-dom';

const navItems = [
  { to: '/upload', label: '上传中心', hint: '文档与模板接入' },
  { to: '/documents', label: '文档详情', hint: '解析进度、blocks 与 facts' },
  { to: '/facts', label: '事实复核', hint: '筛选、追溯与人工确认' },
  { to: '/agent', label: '回填与 Agent', hint: '模板回填、结果追溯与 Agent 执行' },
  { to: '/benchmarks', label: 'Benchmark', hint: '事实评测与模板基准' },
];

export default function NavSidebar() {
  return (
    <aside className="glass-panel hidden w-72 shrink-0 rounded-[28px] border border-white/60 p-6 shadow-card lg:block">
      <div className="mb-10">
        <div className="text-xs font-semibold uppercase tracking-[0.28em] text-teal">DocFusion Copilot</div>
        <h1 className="mt-3 text-3xl font-semibold text-ink">比赛演示控制台</h1>
        <p className="mt-3 text-sm leading-6 text-slate-600">
          聚焦文档上传、异步任务状态、模板回填结果和来源追溯四条核心链路。
        </p>
      </div>

      <nav className="space-y-3">
        {navItems.map((item) => (
          <NavLink
            key={item.to}
            to={item.to}
            className={({ isActive }) =>
              [
                'block rounded-2xl border px-4 py-4 transition',
                isActive
                  ? 'border-amber-300 bg-amber-50 text-ink shadow-sm'
                  : 'border-transparent bg-white/50 text-slate-600 hover:border-white hover:bg-white/80',
              ].join(' ')
            }
          >
            <div className="text-base font-semibold">{item.label}</div>
            <div className="mt-1 text-sm text-slate-500">{item.hint}</div>
          </NavLink>
        ))}
      </nav>

      <div className="mt-10 rounded-2xl bg-ink p-5 text-white">
        <div className="text-xs uppercase tracking-[0.25em] text-white/60">当前目标</div>
        <div className="mt-3 text-lg font-semibold">先把演示链路做稳，再补接口联调。</div>
      </div>
    </aside>
  );
}