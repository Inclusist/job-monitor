import api from './api';
import type { ProfileResponse } from '../types';

export async function getProfile(): Promise<ProfileResponse> {
  const { data } = await api.get<ProfileResponse>('/api/profile');
  return data;
}

export async function uploadCV(
  file: File,
  setPrimary: boolean = true
): Promise<{ success: boolean; cv_id?: number; message?: string; parsing_cost?: number; error?: string }> {
  const formData = new FormData();
  formData.append('file', file);
  formData.append('set_primary', setPrimary.toString());
  const { data } = await api.post('/api/upload-cv', formData, {
    headers: { 'Content-Type': 'multipart/form-data' },
    timeout: 120000,
  });
  return data;
}

export async function deleteCV(cvId: number): Promise<{ success: boolean; error?: string }> {
  const { data } = await api.post(`/api/delete-cv/${cvId}`);
  return data;
}

export async function setPrimaryCV(cvId: number): Promise<{ success: boolean; error?: string }> {
  const { data } = await api.post(`/api/set-primary-cv/${cvId}`);
  return data;
}

export async function updateProfile(
  payload: { user?: Record<string, string>; profile?: Record<string, unknown> }
): Promise<{ success: boolean; error?: string }> {
  const { data } = await api.put('/api/profile', payload);
  return data;
}

export async function updateContactInfo(
  payload: { resume_name?: string; resume_email?: string; resume_phone?: string }
): Promise<{ success: boolean; error?: string }> {
  const { data } = await api.post('/api/update-contact-info', payload);
  return data;
}

export async function saveProjects(
  projects: string[]
): Promise<{ success: boolean; error?: string }> {
  const { data } = await api.post('/api/save-projects', { projects });
  return data;
}
