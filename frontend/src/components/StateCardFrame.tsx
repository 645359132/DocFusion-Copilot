import type { ReactNode } from 'react';

type StateTone = 'empty' | 'error' | 'loading';

const toneClasses: Record<StateTone, string> = {
  empty: 'border-dashed border-slate-300 bg-white/70',
  error: 'border-rose-200 bg-rose-50/90',
  loading: 'border-sky-200 bg-sky-50/90',
};

const badgeClasses: Record<StateTone, string> = {
  empty: 'bg-slate-100 text-slate-600',
  error: 'bg-rose-100 text-rose-700',
  loading: 'bg-sky-100 text-sky-700',
};

export default function StateCardFrame({
  tone,
  badge,
  title,
  description,
  children,
}: {
  tone: StateTone;
  badge: string;
  title: string;
  description: string;
  children?: ReactNode;
}) {
  return (
    <div className={`rounded-[24px] border p-6 ${toneClasses[tone]}`}>
      <div className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold uppercase tracking-[0.18em] ${badgeClasses[tone]}`}>
        {badge}
      </div>
      <div className="mt-4 text-lg font-semibold text-ink">{title}</div>
      <div className="mt-2 text-sm leading-7 text-slate-600">{description}</div>
      {children ? <div className="mt-4">{children}</div> : null}
    </div>
  );
}