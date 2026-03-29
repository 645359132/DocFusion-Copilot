import { useEffect, useMemo, useState } from 'react';
import AppButton from '@/components/AppButton';
import EmptyStateCard from '@/components/EmptyStateCard';
import ErrorStateCard from '@/components/ErrorStateCard';
import LoadingStateCard from '@/components/LoadingStateCard';
import { getBenchmarkReport, getTaskStatus, submitFactEvaluation, submitTemplateBenchmark } from '@/services';
import type { BenchmarkReportResponse } from '@/services';
import { useUiStore } from '@/stores/uiStore';

export default function BenchmarkLabPage() {
  const uploadedDocuments = useUiStore((state) => state.uploadedDocuments);
  const currentDocumentSetId = useUiStore((state) => state.currentDocumentSetId);
  const upsertTaskSnapshot = useUiStore((state) => state.upsertTaskSnapshot);
  const pushToast = useUiStore((state) => state.pushToast);

  const [annotationFile, setAnnotationFile] = useState<File | null>(null);
  const [benchmarkTemplateFile, setBenchmarkTemplateFile] = useState<File | null>(null);
  const [expectedResultFile, setExpectedResultFile] = useState<File | null>(null);
  const [minConfidence, setMinConfidence] = useState('0.7');
  const [fillMode, setFillMode] = useState('canonical');
  const [isSubmittingFactBenchmark, setIsSubmittingFactBenchmark] = useState(false);
  const [isSubmittingTemplateBenchmark, setIsSubmittingTemplateBenchmark] = useState(false);
  const [isLoadingReport, setIsLoadingReport] = useState(false);
  const [pageError, setPageError] = useState<string | null>(null);
  const [latestBenchmarkTaskId, setLatestBenchmarkTaskId] = useState<string | null>(null);
  const [benchmarkReport, setBenchmarkReport] = useState<BenchmarkReportResponse | null>(null);

  const documentIds = useMemo(() => uploadedDocuments.map((item) => item.document.doc_id), [uploadedDocuments]);

  useEffect(() => {
    if (!latestBenchmarkTaskId) {
      return undefined;
    }

    const timer = window.setInterval(async () => {
      try {
        const task = await getTaskStatus(latestBenchmarkTaskId);
        upsertTaskSnapshot(task);
        if (['succeeded', 'completed', 'success', 'failed'].includes(task.status)) {
          window.clearInterval(timer);
        }
      } catch {
        window.clearInterval(timer);
      }
    }, 3000);

    return () => window.clearInterval(timer);
  }, [latestBenchmarkTaskId, upsertTaskSnapshot]);

  async function handleSubmitFactBenchmark() {
    if (!annotationFile) {
      setPageError('请先选择标注事实文件。');
      return;
    }

    setIsSubmittingFactBenchmark(true);
    setPageError(null);

    try {
      const response = await submitFactEvaluation({
        annotationFile,
        documentIds: documentIds.length ? documentIds : undefined,
        canonicalOnly: true,
        minConfidence: Number(minConfidence),
      });
      setLatestBenchmarkTaskId(response.task_id);
      setBenchmarkReport(null);
      pushToast({
        title: '事实评测任务已提交',
        message: `${response.annotation_name} 已生成任务 ${response.task_id}。`,
        tone: 'success',
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : '事实评测提交失败。';
      setPageError(message);
    } finally {
      setIsSubmittingFactBenchmark(false);
    }
  }

  async function handleSubmitTemplateBenchmark() {
    if (!benchmarkTemplateFile || !expectedResultFile) {
      setPageError('请先选择模板文件和期望结果文件。');
      return;
    }

    setIsSubmittingTemplateBenchmark(true);
    setPageError(null);

    try {
      const response = await submitTemplateBenchmark({
        templateFile: benchmarkTemplateFile,
        expectedResultFile,
        documentSetId: currentDocumentSetId ?? 'default',
        fillMode,
        documentIds: documentIds.length ? documentIds : undefined,
      });
      setLatestBenchmarkTaskId(response.task_id);
      setBenchmarkReport(null);
      pushToast({
        title: '模板 benchmark 任务已提交',
        message: `${response.template_name} 已生成任务 ${response.task_id}。`,
        tone: 'success',
      });
    } catch (error) {
      const message = error instanceof Error ? error.message : '模板 benchmark 提交失败。';
      setPageError(message);
    } finally {
      setIsSubmittingTemplateBenchmark(false);
    }
  }

  async function handleLoadReport() {
    if (!latestBenchmarkTaskId) {
      setPageError('当前没有 benchmark task_id。');
      return;
    }

    setIsLoadingReport(true);
    setPageError(null);

    try {
      const report = await getBenchmarkReport(latestBenchmarkTaskId);
      setBenchmarkReport(report);
    } catch (error) {
      const message = error instanceof Error ? error.message : '加载 benchmark 报告失败。';
      setPageError(message);
    } finally {
      setIsLoadingReport(false);
    }
  }

  return (
    <div className="grid gap-6 xl:grid-cols-[1.1fr_0.9fr]">
      <section className="space-y-6">
        <div className="glass-panel rounded-[28px] border border-white/70 p-6 shadow-card">
          <div className="flex flex-col gap-4 lg:flex-row lg:items-center lg:justify-between">
            <div>
              <div className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">Benchmark Lab</div>
              <h3 className="mt-2 text-2xl font-semibold text-ink">评测与基准页</h3>
            </div>
            <AppButton onClick={handleLoadReport} variant="secondary" loading={isLoadingReport} loadingText="读取中...">
              读取最新报告
            </AppButton>
          </div>

          {pageError ? <div className="mt-4"><ErrorStateCard title="Benchmark 操作失败" description={pageError} /></div> : null}
          {isLoadingReport && !benchmarkReport ? <div className="mt-4"><LoadingStateCard title="正在读取评测报告" description="前端正在请求 benchmark report，用于展示当前任务的指标与明细。" /></div> : null}

          <div className="mt-6 grid gap-6 lg:grid-cols-2">
            <div className="rounded-[24px] border border-white/80 bg-white/85 p-5">
              <div className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">事实抽取评测</div>
              <div className="mt-4 space-y-4">
                <FileInput label="annotation_file" file={annotationFile} onChange={setAnnotationFile} accept=".json,.xlsx,.csv,.md,.txt" />
                <label className="block">
                  <div className="mb-2 text-sm font-semibold text-ink">min_confidence</div>
                  <input
                    value={minConfidence}
                    onChange={(event) => setMinConfidence(event.target.value)}
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-teal"
                  />
                </label>
                <AppButton onClick={handleSubmitFactBenchmark} loading={isSubmittingFactBenchmark} loadingText="提交中...">
                  提交 facts evaluate
                </AppButton>
              </div>
            </div>

            <div className="rounded-[24px] border border-white/80 bg-white/85 p-5">
              <div className="text-xs font-semibold uppercase tracking-[0.22em] text-slate-400">模板回填 benchmark</div>
              <div className="mt-4 space-y-4">
                <FileInput label="template_file" file={benchmarkTemplateFile} onChange={setBenchmarkTemplateFile} accept=".xlsx,.docx" />
                <FileInput label="expected_result_file" file={expectedResultFile} onChange={setExpectedResultFile} accept=".xlsx,.docx" />
                <label className="block">
                  <div className="mb-2 text-sm font-semibold text-ink">fill_mode</div>
                  <select
                    value={fillMode}
                    onChange={(event) => setFillMode(event.target.value)}
                    className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 outline-none transition focus:border-teal"
                  >
                    <option value="canonical">canonical</option>
                    <option value="candidate">candidate</option>
                  </select>
                </label>
                <AppButton
                  onClick={handleSubmitTemplateBenchmark}
                  variant="accent"
                  loading={isSubmittingTemplateBenchmark}
                  loadingText="提交中..."
                >
                  提交 template benchmark
                </AppButton>
              </div>
            </div>
          </div>
        </div>

        <div className="glass-panel rounded-[28px] border border-white/70 p-6 shadow-card">
          <div className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">报告输出</div>
          <div className="mt-4">
            {benchmarkReport ? (
              <div className="space-y-4">
                <ReportLine label="task_id" value={benchmarkReport.task_id} />
                <ReportLine label="task_type" value={benchmarkReport.task_type} />
                <div className="rounded-[24px] bg-slate-50 p-4">
                  <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">report</div>
                  <pre className="mt-3 overflow-auto text-xs leading-6 text-slate-700">{JSON.stringify(benchmarkReport.report, null, 2)}</pre>
                </div>
              </div>
            ) : (
              <EmptyStateCard title="尚未读取报告" description="提交 benchmark 任务后，等任务结束，再点击读取最新报告。" />
            )}
          </div>
        </div>
      </section>

      <section className="space-y-6">
        <div className="glass-panel rounded-[28px] border border-white/70 p-6 shadow-card">
          <div className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">当前批次上下文</div>
          <div className="mt-4 space-y-3 text-sm text-slate-600">
            <div>document_set_id：{currentDocumentSetId ?? 'default'}</div>
            <div>可用 document_ids：{documentIds.join(', ') || '暂无'}</div>
          </div>
        </div>

        <div className="glass-panel rounded-[28px] border border-white/70 p-6 shadow-card">
          <div className="text-xs font-semibold uppercase tracking-[0.24em] text-slate-400">已接后端能力</div>
          <ul className="mt-4 space-y-3 text-sm leading-7 text-slate-600">
            <li>POST /api/v1/benchmarks/facts/evaluate：提交事实抽取评测。</li>
            <li>POST /api/v1/benchmarks/templates/fill：提交模板回填 benchmark。</li>
            <li>GET /api/v1/benchmarks/reports/{'{task_id}'}：读取评测报告。</li>
          </ul>
        </div>
      </section>
    </div>
  );
}

function FileInput({
  label,
  file,
  onChange,
  accept,
}: {
  label: string;
  file: File | null;
  onChange: (file: File | null) => void;
  accept?: string;
}) {
  return (
    <label className="block">
      <div className="mb-2 text-sm font-semibold text-ink">{label}</div>
      <input
        type="file"
        accept={accept}
        onChange={(event) => onChange(event.target.files?.[0] ?? null)}
        className="w-full rounded-2xl border border-slate-200 bg-white px-4 py-3 text-sm text-slate-700 file:mr-4 file:rounded-full file:border-0 file:bg-amber-100 file:px-3 file:py-2 file:text-xs file:font-semibold file:text-amber-900"
      />
      {file ? <div className="mt-2 text-xs text-slate-500">已选择：{file.name}</div> : null}
    </label>
  );
}

function ReportLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-2xl bg-slate-50 px-4 py-3">
      <div className="text-xs font-semibold uppercase tracking-[0.2em] text-slate-400">{label}</div>
      <div className="mt-2 break-all text-sm text-ink">{value}</div>
    </div>
  );
}