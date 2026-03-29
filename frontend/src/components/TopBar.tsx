import { useLocation } from 'react-router-dom';
import { useMemo } from 'react';
import { useUiStore } from '@/stores/uiStore';

const titles: Record<string, { title: string; subtitle: string }> = {
  '/upload': {
    title: '上传中心',
    subtitle: '统一管理文档接入、模板上传和任务启动入口。',
  },
  '/documents': {
    title: '文档详情',
    subtitle: '查看文档解析进度、blocks 和抽取 facts。',
  },
  '/facts': {
    title: '事实复核',
    subtitle: '面向评委可见的事实筛选、人工确认与证据链查看。',
  },
  '/agent': {
    title: '回填与 Agent',
    subtitle: '模板回填、结果追溯和自然语言 Agent 执行。',
  },
  '/benchmarks': {
    title: 'Benchmark',
    subtitle: '内部评测页，用于展示事实抽取和模板回填的量化报告。',
  },
};

export default function TopBar() {
  const location = useLocation();
  const current = titles[location.pathname] ?? titles['/upload'];
  const uploadedDocuments = useUiStore((state) => state.uploadedDocuments);
  const selectedTemplateName = useUiStore((state) => state.selectedTemplateName);
  const taskSnapshots = useUiStore((state) => state.taskSnapshots);
  const currentDocumentSetId = useUiStore((state) => state.currentDocumentSetId);

  const summaryCards = useMemo(() => {
    const tasks = Object.values(taskSnapshots);
    const completedCount = tasks.filter((task) => ['succeeded', 'completed', 'success'].includes(task.status)).length;
    const processingCount = tasks.filter((task) => ['queued', 'pending', 'running', 'processing'].includes(task.status)).length;

    return [
      { label: '已上传文档', value: `${uploadedDocuments.length} 份`, tone: 'text-ember' },
      { label: '已完成任务', value: `${completedCount} 项`, tone: 'text-teal' },
      { label: '当前批次', value: currentDocumentSetId ?? (selectedTemplateName ? '待绑定' : '未建立'), tone: 'text-ink' },
    ];
  }, [currentDocumentSetId, selectedTemplateName, taskSnapshots, uploadedDocuments.length]);

  return (
    <header className="glass-panel rounded-[28px] border border-white/60 p-6 shadow-card">
      <div className="flex flex-col gap-6 xl:flex-row xl:items-end xl:justify-between">
        <div>
          <div className="text-xs font-semibold uppercase tracking-[0.28em] text-slate-500">A23 比赛版前端</div>
          <h2 className="mt-3 text-3xl font-semibold text-ink">{current.title}</h2>
          <p className="mt-2 max-w-2xl text-sm leading-6 text-slate-600">{current.subtitle}</p>
        </div>

        <div className="grid gap-3 sm:grid-cols-3">
          {summaryCards.map((card) => (
            <div key={card.label} className="rounded-2xl border border-white/70 bg-white/80 px-4 py-4">
              <div className="text-xs uppercase tracking-[0.22em] text-slate-400">{card.label}</div>
              <div className={`mt-3 text-2xl font-semibold ${card.tone}`}>{card.value}</div>
            </div>
          ))}
        </div>
      </div>
    </header>
  );
}