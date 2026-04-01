import { requestJson } from '@/services/http';
import { buildApiUrl } from '@/services/http';
import type { BlockResponse, DocumentResponse, FactResponse } from '@/services/types';

export async function listDocuments(): Promise<DocumentResponse[]> {
  return requestJson<DocumentResponse[]>('/api/v1/documents');
}

export async function getDocumentDetail(docId: string): Promise<DocumentResponse> {
  return requestJson<DocumentResponse>(`/api/v1/documents/${encodeURIComponent(docId)}`);
}

export async function getDocumentBlocks(docId: string): Promise<BlockResponse[]> {
  return requestJson<BlockResponse[]>(`/api/v1/documents/${encodeURIComponent(docId)}/blocks`);
}

export async function getDocumentFacts(docId: string): Promise<FactResponse[]> {
  return requestJson<FactResponse[]>(`/api/v1/documents/${encodeURIComponent(docId)}/facts`);
}

export async function deleteDocument(docId: string): Promise<{ doc_id: string; deleted: boolean }> {
  return requestJson<{ doc_id: string; deleted: boolean }>(`/api/v1/documents/${encodeURIComponent(docId)}`, {
    method: 'DELETE',
  });
}

export function getDocumentRawUrl(docId: string): string {
  return buildApiUrl(`/api/v1/documents/${encodeURIComponent(docId)}/raw`);
}