import AppButton from '@/components/AppButton';
import EmptyStateCard from '@/components/EmptyStateCard';
import ErrorStateCard from '@/components/ErrorStateCard';
import LoadingStateCard from '@/components/LoadingStateCard';
import { useUiStore } from '@/stores/uiStore';

export default function TraceabilityDrawer() {
  const tracePanel = useUiStore((state) => state.tracePanel);
  const closeTrace = useUiStore((state) => state.closeTrace);
  const activeTrace = tracePanel.data;
  const isVisible = tracePanel.loading || Boolean(tracePanel.error) || Boolean(activeTrace);

  return (
    <div
      className={[
        'fixed inset-y-6 right-6 z-20 w-[min(420px,calc(100vw-1.5rem))] rounded-[28px] border border-white/70 bg-white/95 p-6 shadow-card transition duration-300',
        isVisible ? 'translate-x-0 opacity-100' : 'pointer-events-none translate-x-12 opacity-0',
      ].join(' ')}
    >
      {isVisible ? (
        <>
          <div className="flex items-start justify-between gap-4">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">来源追溯</div>
              <h3 className="mt-2 text-2xl font-semibold text-ink">{tracePanel.cellLabel ? `单元格 ${tracePanel.cellLabel}` : '事实追溯'}</h3>
            </div>
            <AppButton
              onClick={closeTrace}
              variant="ghost"
              size="sm"
            >
              关闭
            </AppButton>
          </div>

          {tracePanel.loading ? (
            <div className="mt-6">
              <LoadingStateCard title="正在查询来源追溯" description="正在向后端请求事实来源、文档区块和模板使用记录。" />
            </div>
          ) : null}

          {tracePanel.error ? (
            <div className="mt-6">
              <ErrorStateCard title="追溯查询失败" description={tracePanel.error} />
            </div>
          ) : null}

          {activeTrace ? (
            <div className="mt-6 space-y-4 text-sm text-slate-600">
              <Section label="事实 ID" value={activeTrace.fact.fact_id} />
              <Section label="目标字段" value={activeTrace.fact.field_name} />
              <Section label="实体名称" value={activeTrace.fact.entity_name} />
              <Section label="来源文档" value={activeTrace.document?.file_name ?? '暂无文档信息'} />
              <Section label="来源路径" value={activeTrace.block?.section_path.join(' / ') || '暂无区块路径'} />
              <Section label="置信度" value={activeTrace.fact.confidence.toFixed(2)} />
              <div className="rounded-2xl bg-mist p-4">
                <div className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">原文证据</div>
                <p className="mt-3 text-sm leading-7 text-ink">{activeTrace.block?.text || activeTrace.fact.source_span || '暂无证据文本。'}</p>
              </div>
              <div className="rounded-2xl border border-dashed border-slate-300 p-4">
                <div className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">模板使用记录</div>
                <div className="mt-3 space-y-3">
                  {activeTrace.usages.length ? (
                    activeTrace.usages.map((usage, index) => (
                      <div key={`${String(usage.task_id)}-${index}`} className="rounded-2xl bg-slate-50 px-4 py-3 text-sm text-slate-600">
                        <div>任务：{String(usage.task_id ?? '-')}</div>
                        <div>输出文件：{String(usage.output_file_name ?? '-')}</div>
                        <div>工作表：{String(usage.sheet_name ?? '-')}</div>
                        <div>单元格：{String(usage.cell_ref ?? '-')}</div>
                      </div>
                    ))
                  ) : (
                    <EmptyStateCard title="暂无模板使用记录" description="当前 fact 已找到来源，但还没有被任何模板回填结果引用。" />
                  )}
                </div>
              </div>
            </div>
          ) : null}
        </>
      ) : null}
    </div>
  );
}

function Section({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl border border-slate-100 bg-slate-50 px-4 py-3">
      <div className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">{label}</div>
      <div className="mt-2 text-base font-medium text-ink">{value}</div>
    </div>
  );
}