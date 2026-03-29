import { useEffect, useMemo, useState } from 'react';
import AppButton from '@/components/AppButton';
import EmptyStateCard from '@/components/EmptyStateCard';
import ErrorStateCard from '@/components/ErrorStateCard';
import LoadingStateCard from '@/components/LoadingStateCard';
import { listFacts, reviewFact } from '@/services';
import type { FactResponse } from '@/services';
import { useUiStore } from '@/stores/uiStore';

const reviewStatuses = ['pending_review', 'confirmed', 'rejected'] as const;

export default function FactsReviewPage() {
  const [facts, setFacts] = useState<FactResponse[]>([]);
  const [isLoading, setIsLoading] = useState(true);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [reviewingFactId, setReviewingFactId] = useState<string | null>(null);
  const [statusFilter, setStatusFilter] = useState<string>('all');
  const [fieldKeyword, setFieldKeyword] = useState('');
  const uploadedDocuments = useUiStore((state) => state.uploadedDocuments);
  const openTraceByFactId = useUiStore((state) => state.openTraceByFactId);
  const pushToast = useUiStore((state) => state.pushToast);

  const uploadedDocumentIds = useMemo(() => uploadedDocuments.map((item) => item.document.doc_id), [uploadedDocuments]);

  async function loadFacts(showLoading: boolean) {
    if (showLoading) {
      setIsLoading(true);
    } else {
      setIsRefreshing(true);
    }
    setPageError(null);

    try {
      const result = await listFacts({
        status: statusFilter === 'all' ? undefined : statusFilter,
        fieldName: fieldKeyword.trim() || undefined,
        canonicalOnly: true,
        documentIds: uploadedDocumentIds.length ? uploadedDocumentIds : undefined,
      });
      setFacts(result);
    } catch (error) {
      setPageError(error instanceof Error ? error.message : '事实列表加载失败。');
    } finally {
      setIsLoading(false);
      setIsRefreshing(false);
    }
  }

  useEffect(() => {
    void loadFacts(true);
  }, [statusFilter, uploadedDocumentIds.join('|')]);

  const filteredFacts = useMemo(() => {
    if (!fieldKeyword.trim()) {
      return facts;
    }

    const keyword = fieldKeyword.trim().toLowerCase();
    return facts.filter((fact) => {
      return [fact.field_name, fact.entity_name, fact.value_text]
        .join(' ')
        .toLowerCase()
        .includes(keyword);
    });
  }, [facts, fieldKeyword]);

  async function handleReview(factId: string, status: (typeof reviewStatuses)[number]) {
    setReviewingFactId(factId);
    setPageError(null);

    try {
      const updated = await reviewFact(factId, {
        status,
        reviewer: 'frontend-demo',
        note: '前端复核面板提交',
      });
      setFacts((current) => current.map((fact) => (fact.fact_id === factId ? updated : fact)));
      pushToast({
        title: '事实复核已更新',
        message: `${updated.field_name} 已标记为 ${updated.status}。`,
        tone: 'success',
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : '事实复核失败。';
      setPageError(message);
      pushToast({
        title: '复核失败',
        message,
        tone: 'error',
      });
    } finally {
      setReviewingFactId(null);
    }
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[1.2fr_0.8fr]">
      <section className="glass-panel rounded-[28px] border border-white/70 p-6 shadow-card">
        <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
          <div>
            <div className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">步骤 04</div>
            <h3 className="mt-2 text-2xl font-semibold text-ink">事实复核台</h3>
          </div>
          <AppButton onClick={() => void loadFacts(false)} variant="secondary" loading={isRefreshing} loadingText="刷新中...">
            刷新事实
          </AppButton>
        </div>

        <div className="mt-6 grid gap-4 md:grid-cols-[0.8fr_1.2fr]">
          <label className="block">
            <div className="mb-2 text-sm font-semibold text-ink">状态筛选</div>
            <select
              value={statusFilter}
              onChange={(event) => setStatusFilter(event.target.value)}
              className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-teal"
            >
              <option value="all">全部状态</option>
              <option value="pending_review">pending_review</option>
              <option value="confirmed">confirmed</option>
              <option value="rejected">rejected</option>
            </select>
          </label>
          <label className="block">
            <div className="mb-2 text-sm font-semibold text-ink">字段 / 实体搜索</div>
            <input
              value={fieldKeyword}
              onChange={(event) => setFieldKeyword(event.target.value)}
              placeholder="输入字段名、实体名或值"
              className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-teal"
            />
          </label>
        </div>

        {isLoading ? <div className="mt-4"><LoadingStateCard title="正在加载事实列表" description="前端正在调用 GET /api/v1/facts，请稍候。" /></div> : null}
        {pageError ? <div className="mt-4"><ErrorStateCard title="事实列表加载失败" description={pageError} /></div> : null}

        <div className="mt-6 space-y-4">
          {filteredFacts.length ? (
            filteredFacts.map((fact) => (
              <article key={fact.fact_id} className="rounded-[24px] border border-white/80 bg-white/85 p-5">
                <div className="flex flex-col gap-4 lg:flex-row lg:items-start lg:justify-between">
                  <div>
                    <div className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">{fact.entity_name}</div>
                    <h4 className="mt-2 text-xl font-semibold text-ink">{fact.field_name}</h4>
                    <p className="mt-2 text-sm leading-7 text-slate-600">{fact.value_text || String(fact.value_num ?? '-')}</p>
                    <div className="mt-2 text-xs text-slate-500">
                      fact_id: {fact.fact_id} · confidence: {(fact.confidence * 100).toFixed(1)}% · status: {fact.status}
                    </div>
                  </div>
                  <div className="flex flex-wrap gap-2">
                    <AppButton size="sm" variant="ghost" onClick={() => openTraceByFactId(fact.fact_id, fact.field_name)}>
                      查看追溯
                    </AppButton>
                    <AppButton
                      size="sm"
                      variant="secondary"
                      onClick={() => void handleReview(fact.fact_id, 'confirmed')}
                      disabled={reviewingFactId === fact.fact_id}
                    >
                      确认
                    </AppButton>
                    <AppButton
                      size="sm"
                      variant="accent"
                      onClick={() => void handleReview(fact.fact_id, 'rejected')}
                      disabled={reviewingFactId === fact.fact_id}
                    >
                      驳回
                    </AppButton>
                  </div>
                </div>
              </article>
            ))
          ) : !isLoading ? (
            <EmptyStateCard title="没有可显示的 facts" description="先上传文档并等待抽取完成，或调整筛选条件后重试。" />
          ) : null}
        </div>
      </section>

      <section className="space-y-6">
        <div className="glass-panel rounded-[28px] border border-white/70 p-6 shadow-card">
          <div className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">复核说明</div>
          <ul className="mt-4 space-y-3 text-sm leading-7 text-slate-600">
            <li>当前列表走 GET /api/v1/facts，默认只看 canonical facts。</li>
            <li>复核按钮会调用 PATCH /api/v1/facts/{'{fact_id}'}/review。</li>
            <li>来源追溯继续复用右侧抽屉，不额外开新弹窗。</li>
          </ul>
        </div>

        <div className="glass-panel rounded-[28px] border border-white/70 p-6 shadow-card">
          <div className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">当前范围</div>
          <div className="mt-4 rounded-2xl bg-slate-50 px-4 py-4 text-sm leading-7 text-slate-600">
            当前页面优先展示本次上传文档对应的 facts，并支持快速复核。后续如果需要全库视图，可再增加 document_set 级筛选或分页。
          </div>
        </div>
      </section>
    </div>
  );
}