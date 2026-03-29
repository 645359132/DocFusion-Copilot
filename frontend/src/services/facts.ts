import { requestJson } from '@/services/http';
import type { FactQueryParams, FactResponse, FactReviewRequest } from '@/services/types';

function buildFactsQuery(params: FactQueryParams = {}): string {
  const searchParams = new URLSearchParams();

  if (params.entityName) {
    searchParams.set('entity_name', params.entityName);
  }
  if (params.fieldName) {
    searchParams.set('field_name', params.fieldName);
  }
  if (params.status) {
    searchParams.set('status', params.status);
  }
  if (typeof params.minConfidence === 'number') {
    searchParams.set('min_confidence', String(params.minConfidence));
  }
  if (typeof params.canonicalOnly === 'boolean') {
    searchParams.set('canonical_only', String(params.canonicalOnly));
  }
  if (params.documentIds?.length) {
    searchParams.set('document_ids', params.documentIds.join(','));
  }

  const query = searchParams.toString();
  return query ? `/api/v1/facts?${query}` : '/api/v1/facts';
}

export async function listFacts(params: FactQueryParams = {}): Promise<FactResponse[]> {
  return requestJson<FactResponse[]>(buildFactsQuery(params));
}

export async function reviewFact(factId: string, payload: FactReviewRequest): Promise<FactResponse> {
  return requestJson<FactResponse>(`/api/v1/facts/${encodeURIComponent(factId)}/review`, {
    method: 'PATCH',
    headers: {
      'Content-Type': 'application/json',
    },
    body: JSON.stringify(payload),
  });
}