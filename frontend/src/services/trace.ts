import { requestJson } from '@/services/http';
import type { FactTraceResponse, FactResponse } from '@/services/types';

export async function getFactTrace(factId: string): Promise<FactTraceResponse> {
  return requestJson<FactTraceResponse>(`/api/v1/facts/${encodeURIComponent(factId)}/trace`);
}

export async function listLowConfidenceFacts(threshold = 0.7): Promise<FactResponse[]> {
  return requestJson<FactResponse[]>(
    `/api/v1/facts/low-confidence?threshold=${threshold}&canonical_only=true`,
  );
}

export async function reviewFact(
  factId: string,
  payload: { status: string; reviewer?: string; note?: string },
): Promise<FactResponse> {
  return requestJson<FactResponse>(`/api/v1/facts/${encodeURIComponent(factId)}/review`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
}