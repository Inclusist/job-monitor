import api from './api';
import type { User, UserStats } from '../types';

const backendUrl = import.meta.env.VITE_API_URL || '';

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
