import type { TaskStatus } from '@/data/mockData';

const statusMap: Record<TaskStatus, string> = {
  queued: 'bg-slate-100 text-slate-700',
  processing: 'bg-teal-100 text-teal-800',
  completed: 'bg-emerald-100 text-emerald-800',
  warning: 'bg-amber-100 text-amber-800',
};

const labelMap: Record<TaskStatus, string> = {
  queued: '排队中',
  processing: '处理中',
  completed: '已完成',
  warning: '待确认',
};

export default function StatusBadge({ status }: { status: TaskStatus }) {
  return (
    <span className={`inline-flex rounded-full px-3 py-1 text-xs font-semibold ${statusMap[status]}`}>
      {labelMap[status]}
    </span>
  );
}