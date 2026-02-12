import api from './api';

export interface MatchingStatus {
    status: 'idle' | 'running' | 'completed' | 'error';
    progress: number;
    message: string;
    stage: string;
    matches_found?: number;
    jobs_analyzed?: number;
    news_snippets?: string[];
}

export async function runMatching(latestDayOnly: boolean = false): Promise<{ success: boolean; message: string }> {
    const { data } = await api.post('/api/run-matching', { latest_day_only: latestDayOnly });
    return data;
}

export async function getMatchingStatus(): Promise<MatchingStatus> {
    const { data } = await api.get('/api/matching-status');
    return data;
}
