import { requestJson } from '@/services/http';
import type { TaskResponse } from '@/services/types';

export async function getTaskStatus(taskId: string): Promise<TaskResponse> {
  return requestJson<TaskResponse>(`/api/v1/tasks/${encodeURIComponent(taskId)}`);
}