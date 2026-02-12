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
  const prevChunksCompletedRef = useRef<number>(0);

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

  useEffect(() => {
    const currentStatus = query.data?.status;
    const chunksCompleted = query.data?.chunks_completed ?? 0;
    if (!currentStatus) return;

    // Progressive refresh: when chunks_completed counter increases, refresh jobs
    if (currentStatus === 'running' && chunksCompleted > prevChunksCompletedRef.current) {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    }
    prevChunksCompletedRef.current = chunksCompleted;

    // Final refresh: when matching finishes
    if (prevStatusRef.current === 'running' && currentStatus === 'completed') {
      queryClient.invalidateQueries({ queryKey: ['jobs'] });
    }
    prevStatusRef.current = currentStatus;
  }, [query.data?.status, query.data?.chunks_completed, queryClient]);

  return query;
}
