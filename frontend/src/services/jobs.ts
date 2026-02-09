import api from './api';
import type { JobsResponse, JobDetail, MatchingStatus, SearchResult } from '../types';

interface JobsParams {
  priority?: string;
  status?: string;
  min_score?: number;
}

export async function getJobs(params: JobsParams = {}): Promise<JobsResponse> {
  const { data } = await api.get<JobsResponse>('/api/jobs', { params });
  return data;
}

export async function hideJob(jobId: number): Promise<void> {
  await api.post(`/api/jobs/${jobId}/hide`);
}

export async function runMatching(): Promise<{ success: boolean; message?: string; error?: string }> {
  const { data } = await api.post('/api/run-matching');
  return data;
}

export async function getMatchingStatus(): Promise<MatchingStatus> {
  const { data } = await api.get<MatchingStatus>('/api/matching-status');
  return data;
}

export async function getJobDetail(jobId: number): Promise<JobDetail> {
  const { data } = await api.get<JobDetail>(`/api/jobs/${jobId}`);
  return data;
}

export async function claimItems(
  selections: { name: string; type: 'competency' | 'skill'; evidence?: string }[]
): Promise<{ success: boolean; message?: string; error?: string }> {
  const { data } = await api.post('/api/save-competency-evidence', { selections });
  return data;
}

export async function searchJobs(query: string): Promise<{ results: SearchResult[]; stats: Record<string, unknown> }> {
  const { data } = await api.post('/api/search-jobs', { query });
  return data;
}
