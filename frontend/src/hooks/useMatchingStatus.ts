import { useEffect, useRef } from 'react';
import { useQuery, useQueryClient } from '@tanstack/react-query';
import { getMatchingStatus } from '../services/jobs';
import type { MatchingStatus } from '../types';

const IDLE_STATUS: MatchingStatus = {
  status: 'idle',
  progress: 0,
  message: 'Not running',
};

export function useMatchingStatus(enabled: boolean) {
  const queryClient = useQueryClient();
  const prevStatusRef = useRef<string>('idle');

  const query = useQuery({
    queryKey: ['matching-status'],
    queryFn: getMatchingStatus,
    refetchInterval: (query) => {
      const data = query.state.data;
      if (data?.status === 'running') return 1500;
      return false;
    },
    enabled,
    initialData: IDLE_STATUS,
  });

  // When status transitions to completed, invalidate jobs so they auto-refresh
  useEffect(() => {
    const currentStatus = query.data?.status;
    if (!currentStatus) return;

    if (prevStatusRef.current === 'running' && currentStatus === 'completed') {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    }
    prevStatusRef.current = currentStatus;
  }, [query.data?.status, queryClient]);

  return query;
}
