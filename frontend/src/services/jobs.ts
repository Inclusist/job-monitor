import api from './api';
import type { JobsResponse, JobDetail, MatchingStatus, SearchResult, ResumeGenerateRequest, CoverLetterGenerateRequest, DocumentCard } from '../types';

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

export async function generateResume(jobId: number, reqData: ResumeGenerateRequest): Promise<{ success: boolean; resume_html?: string; job_title?: string; company?: string; error?: string }> {
  const { data } = await api.post(`/api/generate-resume/${jobId}`, reqData);
  return data;
}

export async function saveResume(jobId: number, resumeHtml: string): Promise<{ success: boolean; resume_id?: number; pdf_url?: string; error?: string }> {
  const { data } = await api.post(`/api/save-resume/${jobId}`, { resume_html: resumeHtml });
  return data;
}

export async function generateCoverLetter(jobId: number, reqData: CoverLetterGenerateRequest): Promise<{ success: boolean; cover_letter_text?: string; style_name?: string; job_title?: string; company?: string; error?: string }> {
  const { data } = await api.post(`/api/generate-cover-letter/${jobId}`, reqData);
  return data;
}

export async function saveCoverLetter(jobId: number, text: string): Promise<{ success: boolean; cover_letter_id?: number; error?: string }> {
  const { data } = await api.post(`/api/save-cover-letter/${jobId}`, { cover_letter_text: text });
  return data;
}

export async function getDocuments(): Promise<{ documents: DocumentCard[] }> {
  const { data } = await api.get('/api/documents');
  return data;
}

export async function deleteResume(resumeId: number): Promise<{ success: boolean; error?: string }> {
  const { data } = await api.delete(`/api/resumes/${resumeId}`);
  return data;
}

export async function deleteCoverLetter(clId: number): Promise<{ success: boolean; error?: string }> {
  const { data } = await api.delete(`/api/cover-letters/${clId}`);
  return data;
}
