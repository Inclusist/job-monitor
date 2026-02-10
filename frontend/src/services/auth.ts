import api from './api';
import type { User, UserStats } from '../types';

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
  return '/login/google';
}

export function getLinkedInLoginUrl(): string {
  return '/login/linkedin';
}

export function getLogoutUrl(): string {
  return '/logout';
}
