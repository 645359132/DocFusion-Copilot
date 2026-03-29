import { requestJson } from '@/services/http';
import type {
  BenchmarkReportResponse,
  FactEvaluationAcceptedResponse,
  FactEvaluationRequest,
  TemplateBenchmarkAcceptedResponse,
  TemplateBenchmarkRequest,
} from '@/services/types';

export async function submitFactEvaluation(payload: FactEvaluationRequest): Promise<FactEvaluationAcceptedResponse> {
  const formData = new FormData();
  formData.append('annotation_file', payload.annotationFile);
  formData.append('canonical_only', String(payload.canonicalOnly ?? true));

  if (payload.documentIds?.length) {
    formData.append('document_ids', payload.documentIds.join(','));
  }
  if (typeof payload.minConfidence === 'number') {
    formData.append('min_confidence', String(payload.minConfidence));
  }

  return requestJson<FactEvaluationAcceptedResponse>('/api/v1/benchmarks/facts/evaluate', {
    method: 'POST',
    body: formData,
  });
}

export async function submitTemplateBenchmark(payload: TemplateBenchmarkRequest): Promise<TemplateBenchmarkAcceptedResponse> {
  const formData = new FormData();
  formData.append('template_file', payload.templateFile);
  formData.append('expected_result_file', payload.expectedResultFile);
  formData.append('document_set_id', payload.documentSetId ?? 'default');
  formData.append('fill_mode', payload.fillMode ?? 'canonical');

  if (payload.documentIds?.length) {
    formData.append('document_ids', payload.documentIds.join(','));
  }

  return requestJson<TemplateBenchmarkAcceptedResponse>('/api/v1/benchmarks/templates/fill', {
    method: 'POST',
    body: formData,
  });
}

export async function getBenchmarkReport(taskId: string): Promise<BenchmarkReportResponse> {
  return requestJson<BenchmarkReportResponse>(`/api/v1/benchmarks/reports/${encodeURIComponent(taskId)}`);
}