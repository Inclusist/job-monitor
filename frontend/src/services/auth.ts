import api from './api';
import type { User, UserStats } from '../types';

function resolveBackendUrl(): string {
  const raw = import.meta.env.VITE_API_URL || '';
  if (!raw) return '';
  // Ensure the URL has a protocol so the browser treats it as absolute
  if (raw.startsWith('http://') || raw.startsWith('https://')) return raw;
  return `https://${raw}`;
}

const backendUrl = resolveBackendUrl();

interface MeResponse {
  authenticated: boolean;
  user: User;
  stats: UserStats;
}

export async function getMe(): Promise<MeResponse> {
  const { data } = await api.get<MeResponse>('/api/me');
  return data;
}

export function getGoogleLoginUrl(): string {
  return `${backendUrl}/login/google`;
}

export function getLinkedInLoginUrl(): string {
  return `${backendUrl}/login/linkedin`;
}

export function getLogoutUrl(): string {
  return `${backendUrl}/logout`;
}
